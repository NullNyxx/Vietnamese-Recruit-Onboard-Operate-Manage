"""Template provisioning service for the Policy Engine module.

Handles automatic assignment of default policy templates to new tenants
during registration. Copies all templates as tenant-specific PolicyRules
in an atomic operation (all four domains or none).
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.policy.domain.entities import PolicyRule, PolicyTemplate
from src.modules.policy.domain.enums import PolicyDomain
from src.modules.policy.domain.exceptions import TemplateInitializationError
from src.modules.policy.infrastructure.policy_repository import PolicyRepository
from src.modules.policy.infrastructure.template_repository import TemplateRepository

logger = logging.getLogger(__name__)

# All four domains must be provisioned for the operation to succeed.
_REQUIRED_DOMAINS: set[PolicyDomain] = {
    PolicyDomain.ATTENDANCE,
    PolicyDomain.LEAVE,
    PolicyDomain.OVERTIME,
    PolicyDomain.DISCIPLINARY,
}


class TemplateService:
    """Provisions default policy templates for new tenants.

    Reads all templates from the TemplateRepository and creates
    corresponding PolicyRules scoped to the tenant. The operation
    is atomic — if any template fails to copy, all changes are
    rolled back and the tenant is marked as initialization_failed.

    Attributes:
        session: The async database session for transaction management.
        template_repo: Repository for reading policy templates.
        policy_repo: Repository for creating tenant policy rules.
    """

    def __init__(
        self,
        session: AsyncSession,
        template_repo: TemplateRepository,
        policy_repo: PolicyRepository,
    ) -> None:
        """Initialize the TemplateService.

        Args:
            session: An SQLAlchemy AsyncSession for transaction control.
            template_repo: Repository for retrieving policy templates.
            policy_repo: Repository for persisting tenant policy rules.
        """
        self.session = session
        self.template_repo = template_repo
        self.policy_repo = policy_repo

    async def provision_templates(
        self,
        tenant_id: str,
        system_user_id: UUID,
    ) -> list[PolicyRule]:
        """Provision all default templates for a new tenant.

        Copies every PolicyTemplate into a tenant-specific PolicyRule
        as an atomic operation. All four domains (attendance, leave,
        overtime, disciplinary) must be provisioned successfully or
        the entire operation is rolled back.

        Args:
            tenant_id: The tenant identifier to provision templates for.
            system_user_id: The UUID of the system user to record as
                the creator of the provisioned rules.

        Returns:
            A list of created PolicyRule entities for the tenant.

        Raises:
            TemplateInitializationError: If the provisioning fails for
                any reason (no templates found, missing domains, or
                database error). The tenant should be marked as
                initialization_failed by the caller.
        """
        try:
            templates = await self.template_repo.get_all_templates()

            if not templates:
                raise TemplateInitializationError(
                    "No policy templates found in the system. Cannot initialize tenant policies."
                )

            # Verify all required domains are covered
            template_domains = {t.domain for t in templates}
            missing_domains = _REQUIRED_DOMAINS - template_domains
            if missing_domains:
                missing_names = sorted(d.value for d in missing_domains)
                raise TemplateInitializationError(
                    f"Missing templates for domains: {missing_names}. "
                    "All four domains must have at least one template."
                )

            # Create policy rules from templates within a savepoint
            # so we can rollback atomically on failure.
            created_rules: list[PolicyRule] = []

            async with self.session.begin_nested():
                for template in templates:
                    rule = self._create_rule_from_template(
                        template=template,
                        tenant_id=tenant_id,
                        system_user_id=system_user_id,
                    )
                    created_rule = await self.policy_repo.create_rule(rule)
                    created_rules.append(created_rule)

            logger.info(
                "Successfully provisioned %d template rules for tenant '%s' across domains: %s",
                len(created_rules),
                tenant_id,
                sorted(d.value for d in template_domains),
            )

            return created_rules

        except TemplateInitializationError:
            # Re-raise domain errors as-is
            raise
        except Exception as exc:
            logger.error(
                "Failed to provision templates for tenant '%s': %s",
                tenant_id,
                str(exc),
                exc_info=True,
            )
            raise TemplateInitializationError(
                f"Failed to initialize policy templates for tenant '{tenant_id}': "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    def _create_rule_from_template(
        self,
        template: PolicyTemplate,
        tenant_id: str,
        system_user_id: UUID,
    ) -> PolicyRule:
        """Create a PolicyRule from a PolicyTemplate for a specific tenant.

        Maps template fields to the corresponding PolicyRule fields,
        setting template_rule_id to link back to the source template
        and is_custom to False.

        Args:
            template: The source PolicyTemplate to copy from.
            tenant_id: The tenant identifier for the new rule.
            system_user_id: The UUID to use for the created_by field.

        Returns:
            A new PolicyRule entity (not yet persisted).
        """
        return PolicyRule(
            tenant_id=tenant_id,
            domain=template.domain,
            rule_id=template.rule_id,
            name=template.name,
            description=template.description,
            rule_condition=template.rule_condition,
            rule_action=template.rule_action,
            priority=template.priority,
            enabled=template.enabled,
            template_rule_id=template.id,
            is_custom=False,
            is_deleted=False,
            created_by=system_user_id,
        )
