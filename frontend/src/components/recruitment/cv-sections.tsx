import { Badge } from "@/components/ui/badge";
import type { ExperienceItem, EducationItem } from "@/lib/api/recruitment";

interface CVSectionsProps {
  summary: string | undefined;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
}

const EMPTY_PLACEHOLDER = "Chưa có dữ liệu";

/**
 * Displays parsed CV data in organized sections:
 * - Tóm tắt (summary paragraph)
 * - Kỹ năng (skills as badges)
 * - Kinh nghiệm (experience timeline)
 * - Học vấn (education list)
 *
 * Each section shows a "Chưa có dữ liệu" placeholder when data is empty/undefined.
 */
export function CVSections({
  summary,
  skills,
  experience,
  education,
}: CVSectionsProps) {
  return (
    <div className="space-y-6">
      {/* Tóm tắt */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground mb-2">
          Tóm tắt
        </h3>
        {summary ? (
          <p className="text-sm leading-relaxed">{summary}</p>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {EMPTY_PLACEHOLDER}
          </p>
        )}
      </section>

      {/* Kỹ năng */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground mb-2">
          Kỹ năng
        </h3>
        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {EMPTY_PLACEHOLDER}
          </p>
        )}
      </section>

      {/* Kinh nghiệm */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground mb-2">
          Kinh nghiệm
        </h3>
        {experience.length > 0 ? (
          <div className="space-y-3">
            {experience.map((item, index) => (
              <div
                key={`${item.company}-${item.role}-${index}`}
                className="relative pl-4 border-l-2 border-muted"
              >
                <p className="text-sm font-medium">{item.role}</p>
                <p className="text-sm text-muted-foreground">{item.company}</p>
                <p className="text-xs text-muted-foreground">{item.duration}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {EMPTY_PLACEHOLDER}
          </p>
        )}
      </section>

      {/* Học vấn */}
      <section>
        <h3 className="text-sm font-semibold text-muted-foreground mb-2">
          Học vấn
        </h3>
        {education.length > 0 ? (
          <div className="space-y-3">
            {education.map((item, index) => (
              <div
                key={`${item.institution}-${item.degree}-${index}`}
                className="pl-4 border-l-2 border-muted"
              >
                <p className="text-sm font-medium">{item.degree}</p>
                <p className="text-sm text-muted-foreground">
                  {item.institution}
                </p>
                <p className="text-xs text-muted-foreground">{item.year}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {EMPTY_PLACEHOLDER}
          </p>
        )}
      </section>
    </div>
  );
}
