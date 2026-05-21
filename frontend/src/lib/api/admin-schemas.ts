/**
 * Zod validation schemas for admin panel forms.
 *
 * These schemas provide client-side validation for the admin API
 * request payloads before submission.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Whitelist Add Schema
// ---------------------------------------------------------------------------

/**
 * Validates a whitelist entry value — either a full email address
 * (user@domain.com) or a domain pattern (@domain.com).
 */
export const whitelistAddSchema = z.object({
  value: z
    .string()
    .min(3, "Giá trị phải có ít nhất 3 ký tự")
    .max(255, "Giá trị không được vượt quá 255 ký tự")
    .refine(
      (val) => {
        // Domain pattern: starts with @ followed by a valid domain
        const domainPatternRegex = /^@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/;
        // Email: standard email format
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/;
        return domainPatternRegex.test(val) || emailRegex.test(val);
      },
      {
        message: "Phải là email hợp lệ (user@domain.com) hoặc domain (@domain.com)",
      }
    ),
});

export type WhitelistAddFormData = z.infer<typeof whitelistAddSchema>;

// ---------------------------------------------------------------------------
// OAuth Config Update Schema
// ---------------------------------------------------------------------------

/**
 * Validates OAuth configuration update fields:
 * - client_id must be non-empty
 * - client_secret must be non-empty
 * - redirect_uri must be a valid URL starting with https://
 */
export const oauthConfigUpdateSchema = z.object({
  client_id: z
    .string()
    .min(1, "Client ID không được để trống")
    .max(255, "Client ID không được vượt quá 255 ký tự"),
  client_secret: z
    .string()
    .min(1, "Client Secret không được để trống")
    .max(500, "Client Secret không được vượt quá 500 ký tự"),
  redirect_uri: z
    .string()
    .min(1, "Redirect URI không được để trống")
    .max(500, "Redirect URI không được vượt quá 500 ký tự")
    .url("Redirect URI phải là URL hợp lệ")
    .refine(
      (val) => val.startsWith("https://"),
      { message: "Redirect URI phải bắt đầu bằng https://" }
    ),
});

export type OAuthConfigUpdateFormData = z.infer<typeof oauthConfigUpdateSchema>;

// ---------------------------------------------------------------------------
// Role Update Schema
// ---------------------------------------------------------------------------

/**
 * Validates that the role value is either "admin" or "user".
 */
export const roleUpdateSchema = z.object({
  role: z.enum(["admin", "user"], {
    message: "Vai trò phải là 'admin' hoặc 'user'",
  }),
});

export type RoleUpdateFormData = z.infer<typeof roleUpdateSchema>;
