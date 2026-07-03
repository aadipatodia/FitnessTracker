import { AlertTriangle, Calendar, CheckCircle2, Target, TrendingUp } from 'lucide-react'
import { type GoalFeasibility } from '@/lib/api'
import { cn } from '@/lib/utils'
import { FormattedText } from '@/components/FormattedText'

const intensityStyles: Record<string, string> = {
  none: 'bg-muted text-muted-foreground',
  sustainable: 'bg-emerald-500/15 text-emerald-400',
  aggressive: 'bg-amber-500/15 text-amber-400',
  extreme: 'bg-orange-500/15 text-orange-400',
}

function formatIntensity(intensity: string) {
  if (!intensity || intensity === 'none') return null
  return intensity.charAt(0).toUpperCase() + intensity.slice(1)
}

interface GoalPlanAssessmentProps {
  feasibility: GoalFeasibility
  weeksUntilDeadline: number
  needsAck: boolean
  acknowledged: boolean
  onAckChange: (value: boolean) => void
}

export function GoalPlanAssessment({
  feasibility,
  weeksUntilDeadline,
  needsAck,
  acknowledged,
  onAckChange,
}: GoalPlanAssessmentProps) {
  const isPositive = feasibility.realistic && feasibility.intensity !== 'extreme'
  const intensityLabel = formatIntensity(feasibility.intensity)

  const projections = [
    feasibility.projected_body_fat != null && {
      label: 'Body fat',
      value: `${feasibility.projected_body_fat}%`,
    },
    feasibility.projected_weight != null && {
      label: 'Weight',
      value: `${feasibility.projected_weight} kg`,
    },
    feasibility.projected_lift != null && {
      label: 'Lift',
      value: `${feasibility.projected_lift} kg`,
    },
  ].filter(Boolean) as { label: string; value: string }[]

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border',
        isPositive ? 'border-primary/30 bg-primary/5' : 'border-amber-500/40 bg-amber-500/5',
      )}
    >
      <div className="border-b border-border/50 px-4 py-3">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
              isPositive ? 'bg-primary/15 text-primary' : 'bg-amber-500/15 text-amber-400',
            )}
          >
            {isPositive ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            <h3 className="text-sm font-semibold leading-snug text-foreground">
              {feasibility.headline}
            </h3>
            <div className="flex flex-wrap gap-2">
              {weeksUntilDeadline > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-background/60 px-2.5 py-1 text-sm font-medium text-foreground">
                  <Calendar className="h-3 w-3" />
                  {feasibility.recommended_target_date
                    ? `FitAI timeline · ${weeksUntilDeadline} week${weeksUntilDeadline !== 1 ? 's' : ''}`
                    : `${weeksUntilDeadline} week${weeksUntilDeadline !== 1 ? 's' : ''} left`}
                </span>
              )}
              {intensityLabel && (
                <span
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium capitalize',
                    intensityStyles[feasibility.intensity] ?? intensityStyles.none,
                  )}
                >
                  <TrendingUp className="h-3 w-3" />
                  {intensityLabel} plan
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {projections.length > 0 && (
        <div className="grid gap-2 border-b border-border/50 px-4 py-3 sm:grid-cols-3">
          {projections.map(({ label, value }) => (
            <div
              key={label}
              className="rounded-lg border border-border/50 bg-background/40 px-3 py-2"
            >
              <p className="text-label normal-case">{label} by deadline</p>
              <p className="mt-1 text-base font-semibold text-foreground">{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-4 px-4 py-4">
        {feasibility.expected_by_deadline && (
          <section>
            <div className="mb-2 flex items-center gap-1.5 text-label normal-case">
              <Target className="h-3.5 w-3.5" />
              What to expect
            </div>
            <FormattedText text={feasibility.expected_by_deadline} />
          </section>
        )}

        {feasibility.aggressive_plan && (
          <section>
            <div className="mb-2 flex items-center gap-1.5 text-label normal-case">
              <TrendingUp className="h-3.5 w-3.5" />
              Recommended approach
            </div>
            <FormattedText text={feasibility.aggressive_plan} />
          </section>
        )}
      </div>

      {needsAck && (
        <label className="flex cursor-pointer items-start gap-2 border-t border-amber-500/20 px-4 py-3 text-sm">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => onAckChange(e.target.checked)}
            className="mt-1"
          />
          <span className="text-body-secondary">
            I understand the expected outcome above and want to proceed with an{' '}
            <span className="font-medium text-foreground">{feasibility.intensity}</span> plan anyway.
          </span>
        </label>
      )}
    </div>
  )
}
