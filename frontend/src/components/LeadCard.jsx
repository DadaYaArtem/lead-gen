import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Building2,
  Briefcase,
  Copy,
  Check,
  Star,
  ExternalLink,
  AlertCircle,
  MessageSquare,
  Trash2,
  FileSearch,
  Users,
  Globe,
  TrendingUp,
  Layers,
} from "lucide-react";
import { MessageGroup } from "@/components/MessageGroup";
import { LeadChatPanel } from "@/components/LeadChatPanel";

export function LeadCard({ lead, index, isSelected, onSelect, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [researchOpen, setResearchOpen] = useState(false);

  if (lead.status === "failed") {
    return (
      <div
        className={`bg-white rounded-lg border shadow-sm p-5 transition-colors ${isSelected ? "border-amber-400 bg-amber-50/30" : "border-red-200"}`}
        data-testid={`lead-card-${index}`}
      >
        <div className="flex items-start gap-3">
          <Checkbox
            checked={!!isSelected}
            onCheckedChange={onSelect}
            className="mt-0.5 shrink-0 border-red-300 data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500"
          />
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2 flex-wrap">
              {lead.name || "Unknown Lead"}
              {lead.intent && <IntentBadge intent={lead.intent} />}
              {lead.company && (
                <span className="text-slate-400 font-normal">@ {lead.company}</span>
              )}
            </h3>
            <p className="text-sm text-red-600 mt-1">
              Analysis failed: {lead.error || "Unknown error"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const fitScore = lead.fit_score || 0;

  return (
    <div
      className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden"
      data-testid={`lead-card-${index}`}
    >
      {/* Card Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-5 text-left flex items-center justify-between hover:bg-slate-50/50 transition-colors"
        data-testid={`lead-card-toggle-${index}`}
      >
        <div className="flex items-center gap-4 min-w-0">
          {/* Fit Score */}
          <FitScoreBadge score={fitScore} />

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-[#1a2744] truncate">
                {lead.name}
              </h3>
              {lead.intent && <IntentBadge intent={lead.intent} />}
              {lead.profileUrl && (
                <a
                  href={lead.profileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-slate-400 hover:text-[#1a2744] transition-colors"
                  data-testid={`lead-linkedin-link-${index}`}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-500 mt-0.5 flex-wrap">
              {lead.position && (
                <span className="flex items-center gap-1">
                  <Briefcase className="h-3.5 w-3.5" />
                  {lead.position}
                </span>
              )}
              {lead.company && (
                <span className="flex items-center gap-1">
                  <Building2 className="h-3.5 w-3.5" />
                  {lead.company}
                </span>
              )}
              {lead.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {lead.location}
                </span>
              )}
            </div>
            <CompanySnippet basics={lead.analysis?.company_basics} />
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 ml-4">
          {/* Delete button - stop propagation to prevent card toggle */}
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(lead);
              }}
              className="h-8 w-8 p-0 text-slate-400 hover:text-red-500 hover:bg-red-50"
              title="Delete lead"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          
          {lead.messages?.length > 0 && (
            <span className="text-xs text-slate-400">
              {lead.messages.length} messages
            </span>
          )}
          {lead.analysis && (
            <button
              onClick={(e) => { e.stopPropagation(); setResearchOpen(true); }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-[#6366f1] border border-[#6366f1]/30 bg-indigo-50 hover:bg-indigo-100 hover:border-[#6366f1]/60 transition-colors"
              data-testid={`lead-research-button-${index}`}
            >
              <FileSearch className="h-3.5 w-3.5" />
              View Research
            </button>
          )}
          {lead.conversation_id && (
            <button
              onClick={(e) => { e.stopPropagation(); setChatOpen(true); }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-[#10b981] border border-[#10b981]/30 bg-emerald-50 hover:bg-emerald-100 hover:border-[#10b981]/60 transition-colors"
              data-testid={`lead-chat-button-${index}`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Ask AI
            </button>
          )}
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-slate-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-100 px-5 pb-5" data-testid={`lead-card-content-${index}`}>
          {/* Executive Summary */}
          {lead.executive_summary && (
            <div className="mt-4 mb-5">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Executive Summary
              </h4>
              <p className="text-sm leading-relaxed text-slate-700" data-testid={`lead-summary-${index}`}>
                {lead.executive_summary}
              </p>
            </div>
          )}

          {/* Qualification Details */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <MetricCard label="Fit Score" value={`${fitScore}/10`} />
            <MetricCard label="Status" value={lead.qualification_status || "N/A"} />
            <MetricCard
              label="Authority"
              value={lead.analysis?.qualification?.authority_level || "N/A"}
            />
            <MetricCard
              label="Urgency"
              value={lead.analysis?.qualification?.need_urgency || "N/A"}
            />
          </div>

          {/* Recommended Top 3 Messages */}
          {lead.recommended_top_3?.length > 0 && lead.messages?.length > 0 && (
            <div className="mb-5">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Star className="h-3.5 w-3.5 text-amber-500" />
                Top Recommended Messages
              </h4>
              <div className="space-y-2">
                {lead.recommended_top_3.map((msgId) => {
                  const msg = lead.messages.find((m) => m.id === msgId);
                  if (!msg) return null;
                  return (
                    <MessageCard
                      key={msgId}
                      message={msg}
                      highlighted
                      testIdPrefix={`lead-${index}-top`}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* All Messages Grouped by Type */}
          {lead.messages?.length > 0 && (
            <MessageGroup messages={lead.messages} leadIndex={index} />
          )}

          {/* Strategy Notes */}
          {lead.strategy_notes && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                Strategy Notes
              </h4>
              <p className="text-sm text-slate-600">{lead.strategy_notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Per-lead AI chat panel */}
      {lead.conversation_id && (
        <LeadChatPanel
          lead={lead}
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
        />
      )}

      {/* Full research panel */}
      <Sheet open={researchOpen} onOpenChange={setResearchOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader className="mb-4">
            <SheetTitle className="text-lg font-semibold text-slate-900">
              Full Research — {lead.name}
            </SheetTitle>
          </SheetHeader>
          <ResearchPanel analysis={lead.analysis} />
        </SheetContent>
      </Sheet>
    </div>
  );
}

const INTENT_META = {
  interested:       { label: "Interested",       color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  catchup_thanks:   { label: "Catch-up / Thanks", color: "bg-sky-50 text-sky-700 border-sky-200" },
  soft_objection:   { label: "Soft Objection",   color: "bg-amber-50 text-amber-700 border-amber-200" },
  hard_rejection:   { label: "Hard Rejection",   color: "bg-red-50 text-red-700 border-red-200" },
  ooo:              { label: "Out of Office",     color: "bg-slate-100 text-slate-500 border-slate-200" },
  hiring:           { label: "Hiring",            color: "bg-violet-50 text-violet-700 border-violet-200" },
  question:         { label: "Question",          color: "bg-blue-50 text-blue-700 border-blue-200" },
  redirect:         { label: "Redirect",          color: "bg-orange-50 text-orange-700 border-orange-200" },
  not_relevant:     { label: "Not Relevant",      color: "bg-slate-100 text-slate-400 border-slate-200" },
  other:            { label: "Other",             color: "bg-slate-100 text-slate-500 border-slate-200" },
};

function CompanySnippet({ basics }) {
  if (!basics) return null;
  const items = [
    basics.industry && { icon: <Globe className="h-3 w-3" />, text: basics.industry },
    basics.size     && { icon: <Users className="h-3 w-3" />, text: basics.size },
    basics.stage    && { icon: <TrendingUp className="h-3 w-3" />, text: basics.stage },
    basics.founded  && { icon: <Layers className="h-3 w-3" />, text: `est. ${basics.founded}` },
  ].filter(Boolean);

  if (!items.length) return null;
  return (
    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1 text-xs text-slate-400">
          {item.icon}
          {item.text}
        </span>
      ))}
    </div>
  );
}

function IntentBadge({ intent }) {
  const meta = INTENT_META[intent] || { label: intent, color: "bg-slate-100 text-slate-500 border-slate-200" };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${meta.color}`}
      title="Detected intent"
    >
      {meta.label}
    </span>
  );
}

function FitScoreBadge({ score }) {
  let colorClass = "bg-red-50 text-red-700 border-red-200";
  if (score >= 8) colorClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
  else if (score >= 5) colorClass = "bg-amber-50 text-amber-700 border-amber-200";

  return (
    <div
      className={`w-12 h-12 rounded-full border-2 flex items-center justify-center font-bold text-lg shrink-0 ${colorClass}`}
      data-testid="fit-score-badge"
    >
      {score}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg p-3">
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-semibold text-slate-700 mt-0.5 capitalize">{value}</p>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 border-b border-slate-100 pb-1">
      {children}
    </h4>
  );
}

function Pill({ children, color = "slate" }) {
  const colors = {
    slate:  "bg-slate-100 text-slate-600",
    green:  "bg-emerald-50 text-emerald-700",
    amber:  "bg-amber-50 text-amber-700",
    red:    "bg-red-50 text-red-700",
    blue:   "bg-blue-50 text-blue-700",
    indigo: "bg-indigo-50 text-indigo-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colors[color] || colors.slate}`}>
      {children}
    </span>
  );
}

function Field({ label, value }) {
  if (!value || value === "" || value === "not found") return null;
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-slate-700 leading-relaxed">{value}</p>
    </div>
  );
}

function TagList({ label, items }) {
  const arr = Array.isArray(items) ? items : (items ? [String(items)] : []);
  if (!arr.length) return null;
  return (
    <div>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {arr.map((item, i) => <Pill key={i}>{item}</Pill>)}
      </div>
    </div>
  );
}

function urgencyColor(level) {
  if (!level) return "slate";
  const l = level.toLowerCase();
  if (l === "high") return "red";
  if (l === "medium") return "amber";
  if (l === "low") return "green";
  return "slate";
}

function LeadProfileSection({ data }) {
  if (!data) return null;
  const { current_role, career_trajectory, activity_signals } = data;
  return (
    <div className="mb-6">
      <SectionTitle>Lead Profile</SectionTitle>
      <div className="space-y-4">
        {current_role && (
          <div className="p-3 bg-slate-50 rounded-lg space-y-2">
            <p className="text-xs font-semibold text-slate-500">Current Role</p>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Title" value={current_role.title} />
              <Field label="Time in role" value={current_role.time_in_role} />
              <Field label="Department" value={current_role.department} />
              <Field label="Reports to" value={current_role.reports_to} />
              <Field label="Team size" value={current_role.team_size} />
            </div>
            {current_role.insight && (
              <p className="text-xs text-indigo-600 bg-indigo-50 rounded p-2 mt-1">{current_role.insight}</p>
            )}
          </div>
        )}
        {career_trajectory && (
          <div className="space-y-2">
            <Field label="Progression" value={career_trajectory.progression} />
            <Field label="Industry switches" value={career_trajectory.industry_switches} />
            <TagList label="Previous companies" items={career_trajectory.previous_companies} />
            {career_trajectory.insight && (
              <p className="text-xs text-slate-500 italic">{career_trajectory.insight}</p>
            )}
          </div>
        )}
        {activity_signals && (
          <div className="space-y-2">
            <TagList label="Recent post topics" items={activity_signals.recent_posts_topics} />
            <TagList label="Speaking events" items={activity_signals.speaking_events} />
            <TagList label="Certifications" items={activity_signals.certifications} />
            {activity_signals.hiring && (
              <Pill color="amber">Currently Hiring</Pill>
            )}
            {activity_signals.insight && (
              <p className="text-xs text-slate-500 italic">{activity_signals.insight}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CompanySection({ basics, activity }) {
  if (!basics && !activity) return null;
  return (
    <div className="mb-6">
      <SectionTitle>Company</SectionTitle>
      {basics && (
        <div className="p-3 bg-slate-50 rounded-lg mb-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Industry" value={basics.industry} />
            <Field label="Stage" value={basics.stage} />
            <Field label="Founded" value={basics.founded} />
            <Field label="Size" value={basics.size} />
          </div>
          <TagList label="Locations" items={basics.locations} />
          {basics.stage_insight && (
            <p className="text-xs text-indigo-600 bg-indigo-50 rounded p-2">{basics.stage_insight}</p>
          )}
        </div>
      )}
      {activity && (
        <div className="space-y-2">
          {activity.recent_hiring?.open_roles_count > 0 && (
            <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
              <p className="text-xs font-semibold text-amber-700 mb-1">
                Hiring Signal — {activity.recent_hiring.open_roles_count} open roles
              </p>
              <TagList label="Key roles" items={activity.recent_hiring.key_roles} />
              {activity.recent_hiring.insight && (
                <p className="text-xs text-amber-700 mt-1">{activity.recent_hiring.insight}</p>
              )}
            </div>
          )}
          <TagList label="Expansion" items={activity.expansion} />
          <TagList label="Awards" items={activity.awards} />
          {activity.team_growth && <Field label="Team growth" value={activity.team_growth} />}
        </div>
      )}
    </div>
  );
}

function DeepResearchSection({ data }) {
  if (!data) return null;
  const { funding, product, news, competitive_landscape, regulatory_context } = data;
  return (
    <div className="mb-6">
      <SectionTitle>Deep Research</SectionTitle>
      <div className="space-y-4">
        {funding && (funding.last_round || funding.total_raised) && (
          <div className="p-3 bg-slate-50 rounded-lg space-y-2">
            <p className="text-xs font-semibold text-slate-500">Funding</p>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Last round" value={funding.last_round} />
              <Field label="Total raised" value={funding.total_raised} />
            </div>
            <TagList label="Investors" items={funding.investors} />
            {funding.funding_insight && (
              <p className="text-xs text-indigo-600 bg-indigo-50 rounded p-2">{funding.funding_insight}</p>
            )}
          </div>
        )}
        {product && (
          <div className="p-3 bg-slate-50 rounded-lg space-y-2">
            <p className="text-xs font-semibold text-slate-500">Product</p>
            <Field label="Main product" value={product.main_product} />
            <Field label="Platform type" value={product.platform_type} />
            <TagList label="Tech stack" items={product.tech_stack} />
            <TagList label="Recent launches" items={product.recent_launches} />
            {product.product_insight && (
              <p className="text-xs text-indigo-600 bg-indigo-50 rounded p-2">{product.product_insight}</p>
            )}
          </div>
        )}
        {Array.isArray(news) && news.length > 0 && (
          <div>
            <p className="text-xs text-slate-400 mb-2">Recent News</p>
            <div className="space-y-2">
              {news.map((item, i) => (
                <div key={i} className="p-3 bg-slate-50 rounded-lg border-l-2 border-indigo-200">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-slate-700">{item.headline}</p>
                    {item.date && <span className="text-xs text-slate-400 shrink-0">{item.date}</span>}
                  </div>
                  {item.summary && <p className="text-xs text-slate-500 mt-1">{item.summary}</p>}
                  {item.outreach_hook && (
                    <p className="text-xs text-indigo-600 mt-1 italic">Hook: {item.outreach_hook}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        {competitive_landscape && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400">Competitive Landscape</p>
            <TagList label="Competitors" items={competitive_landscape.competitors} />
            <Field label="Market position" value={competitive_landscape.market_position} />
            <Field label="Differentiation" value={competitive_landscape.differentiation} />
            <Field label="Market trend" value={competitive_landscape.market_trend} />
          </div>
        )}
        {regulatory_context?.industry_trend && (
          <div className="p-3 bg-slate-50 rounded-lg space-y-2">
            <p className="text-xs font-semibold text-slate-500">Regulatory Context</p>
            <Field label="Industry trend" value={regulatory_context.industry_trend} />
            <TagList label="Compliance requirements" items={regulatory_context.compliance_requirements} />
            <TagList label="Recent regulations" items={regulatory_context.recent_regulations} />
          </div>
        )}
      </div>
    </div>
  );
}

function PainPointsSection({ painPoints, vendorApproach, timingTriggers }) {
  const hasPainPoints = painPoints && (
    painPoints.role_specific_pain_points?.length ||
    painPoints.stage_specific_pain_points?.length ||
    painPoints.evidence_from_research?.length
  );

  const hasTriggers = timingTriggers && (
    timingTriggers.active_triggers?.length ||
    timingTriggers.urgency_assessment
  );

  if (!hasPainPoints && !vendorApproach && !hasTriggers) return null;

  return (
    <div className="mb-6">
      <SectionTitle>Pain Points & Opportunity</SectionTitle>
      <div className="space-y-4">
        {hasPainPoints && (
          <div className="space-y-2">
            <TagList label="Role-specific pain points" items={painPoints.role_specific_pain_points} />
            <TagList label="Stage-specific pain points" items={painPoints.stage_specific_pain_points} />
            {painPoints.evidence_from_research?.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Evidence from research</p>
                <ul className="space-y-1">
                  {painPoints.evidence_from_research.map((e, i) => (
                    <li key={i} className="text-xs text-slate-600 flex gap-1.5">
                      <span className="text-slate-300 mt-0.5">•</span>{e}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {vendorApproach && (
          <div className="p-3 bg-slate-50 rounded-lg space-y-2">
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold text-slate-500">Vendor Approach</p>
              <Pill>{vendorApproach.current_solution_hypothesis?.replace(/_/g, " ")}</Pill>
              <Pill color={vendorApproach.confidence === "high" ? "green" : vendorApproach.confidence === "medium" ? "amber" : "slate"}>
                {vendorApproach.confidence} confidence
              </Pill>
            </div>
            <Field label="Build vs buy" value={vendorApproach.build_vs_buy_philosophy?.assessment} />
            <Field label="Implications" value={vendorApproach.build_vs_buy_philosophy?.implications} />
            <TagList label="Evidence" items={vendorApproach.evidence} />
          </div>
        )}
        {hasTriggers && (
          <div className="space-y-2">
            {timingTriggers.urgency_assessment && (
              <div className="flex items-center gap-2">
                <p className="text-xs text-slate-400">Urgency:</p>
                <Pill color={urgencyColor(timingTriggers.urgency_assessment.urgency_level)}>
                  {timingTriggers.urgency_assessment.urgency_level}
                </Pill>
                {timingTriggers.urgency_assessment.primary_driver && (
                  <p className="text-xs text-slate-500">{timingTriggers.urgency_assessment.primary_driver}</p>
                )}
              </div>
            )}
            {Array.isArray(timingTriggers.active_triggers) && timingTriggers.active_triggers.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Active triggers</p>
                <div className="space-y-1">
                  {timingTriggers.active_triggers.map((t, i) => (
                    <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded text-xs">
                      <Pill color="red">{t.urgency}</Pill>
                      <div>
                        <p className="text-slate-700 font-medium">{t.trigger}</p>
                        {t.how_it_creates_need && <p className="text-slate-500 mt-0.5">{t.how_it_creates_need}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {timingTriggers.urgency_assessment?.timing_recommendation && (
              <p className="text-xs text-indigo-600 bg-indigo-50 rounded p-2">
                {timingTriggers.urgency_assessment.timing_recommendation}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationSection({ data }) {
  if (!data) return null;
  return (
    <div className="mb-6">
      <SectionTitle>Conversation Analysis</SectionTitle>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {data.conversation_stage && <Pill color="blue">{data.conversation_stage}</Pill>}
          {data.lead_responsiveness && <Pill>{data.lead_responsiveness}</Pill>}
          {data.messages_exchanged > 0 && <Pill>{data.messages_exchanged} messages</Pill>}
        </div>
        <TagList label="Interest signals" items={data.interest_signals} />
        <TagList label="Objections raised" items={data.objections_raised} />
        <TagList label="Questions asked" items={data.questions_asked} />
        {data.rejection_analysis?.rejection_type && data.rejection_analysis.rejection_type !== "not_applicable" && (
          <div className="p-3 bg-red-50 rounded-lg border border-red-100 space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold text-red-700">Rejection</p>
              <Pill color="red">{data.rejection_analysis.rejection_type.replace(/_/g, " ")}</Pill>
            </div>
            <Field label="Evidence" value={data.rejection_analysis.evidence} />
            <Field label="Recommended approach" value={data.rejection_analysis.recommended_approach} />
          </div>
        )}
      </div>
    </div>
  );
}

function RecommendedActionSection({ action, valueProps }) {
  if (!action && !valueProps) return null;
  return (
    <div className="mb-6">
      <SectionTitle>Recommended Action</SectionTitle>
      <div className="space-y-4">
        {action && (
          <div className="p-3 bg-indigo-50 rounded-lg space-y-2">
            <div className="flex flex-wrap gap-2">
              {action.priority && <Pill color="indigo">{action.priority} priority</Pill>}
              {action.timing && <Pill>{action.timing}</Pill>}
            </div>
            <Field label="Next step" value={action.next_step} />
            <Field label="Message angle" value={action.message_angle} />
            <TagList label="Personalization hooks" items={action.personalization_hooks} />
            <TagList label="Questions to ask" items={action.questions_to_ask} />
          </div>
        )}
        {valueProps && (
          <div className="space-y-2">
            <TagList label="Most relevant value props" items={valueProps.most_relevant} />
            <Field label="Differentiation angle" value={valueProps.differentiation_angle} />
            <TagList label="Case studies to mention" items={valueProps.case_studies_to_mention} />
            <Field label="Technical expertise highlight" value={valueProps.technical_expertise_highlight} />
          </div>
        )}
      </div>
    </div>
  );
}

function ResearchPanel({ analysis }) {
  if (!analysis) return <p className="text-sm text-slate-400">No research data available.</p>;

  const fitScore = analysis.qualification?.fit_score;
  const status = analysis.qualification?.status;
  const budgetColor = { high: "green", medium: "amber", low: "red", unknown: "slate" };
  const urgColor = urgencyColor(analysis.qualification?.need_urgency);

  return (
    <div>
      {/* Executive Summary */}
      {analysis.executive_summary && (
        <div className="mb-6 p-4 bg-indigo-50 rounded-lg border border-indigo-100">
          <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-1">Executive Summary</p>
          <p className="text-sm text-slate-700 leading-relaxed">{analysis.executive_summary}</p>
        </div>
      )}

      {/* Qualification snapshot */}
      {analysis.qualification && (
        <div className="mb-6 grid grid-cols-2 gap-2">
          {fitScore !== undefined && (
            <div className="p-3 bg-slate-50 rounded-lg text-center">
              <p className="text-xs text-slate-400">Fit Score</p>
              <p className="text-2xl font-bold text-slate-800">{fitScore}<span className="text-sm font-normal text-slate-400">/10</span></p>
            </div>
          )}
          {status && (
            <div className="p-3 bg-slate-50 rounded-lg text-center">
              <p className="text-xs text-slate-400">Status</p>
              <p className="text-sm font-semibold text-slate-700 capitalize mt-1">{status.replace(/_/g, " ")}</p>
            </div>
          )}
          <div className="flex flex-wrap gap-1.5 col-span-2">
            {analysis.qualification.budget_indicator && (
              <Pill color={budgetColor[analysis.qualification.budget_indicator]}>
                Budget: {analysis.qualification.budget_indicator}
              </Pill>
            )}
            {analysis.qualification.authority_level && (
              <Pill color="blue">{analysis.qualification.authority_level.replace(/_/g, " ")}</Pill>
            )}
            {analysis.qualification.need_urgency && (
              <Pill color={urgColor}>Urgency: {analysis.qualification.need_urgency.replace(/_/g, " ")}</Pill>
            )}
            {analysis.qualification.vendor_readiness && (
              <Pill>{analysis.qualification.vendor_readiness.replace(/_/g, " ")}</Pill>
            )}
          </div>
          {analysis.qualification.reasoning && (
            <p className="text-xs text-slate-500 col-span-2 italic">{analysis.qualification.reasoning}</p>
          )}
        </div>
      )}

      <LeadProfileSection data={analysis.lead_profile} />
      <CompanySection basics={analysis.company_basics} activity={analysis.company_activity} />
      <DeepResearchSection data={analysis.deep_research} />
      <PainPointsSection
        painPoints={analysis.pain_point_analysis}
        vendorApproach={analysis.vendor_approach_inference}
        timingTriggers={analysis.timing_triggers_analysis}
      />
      <ConversationSection data={analysis.conversation_analysis} />
      <RecommendedActionSection action={analysis.recommended_action} valueProps={analysis.interexy_value_props} />
    </div>
  );
}

export function MessageCard({ message, highlighted = false, testIdPrefix = "msg" }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.message);
      setCopied(true);
      toast.success("Message copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        highlighted
          ? "border-amber-200 bg-amber-50/50"
          : "border-slate-200 bg-white hover:bg-slate-50/50"
      }`}
      data-testid={`${testIdPrefix}-message-${message.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge
              variant="outline"
              className="text-[10px] font-medium uppercase tracking-wider px-1.5 py-0"
            >
              {message.type}
            </Badge>
            {highlighted && <Star className="h-3 w-3 text-amber-500 fill-amber-500" />}
          </div>
          <p className="text-sm text-slate-800 leading-relaxed">{message.message}</p>
          {message.rationale && (
            <p className="text-xs text-slate-400 mt-1.5 italic">{message.rationale}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="shrink-0 h-8 w-8 p-0 rounded-full hover:bg-slate-200"
          data-testid={`${testIdPrefix}-copy-${message.id}`}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <Copy className="h-3.5 w-3.5 text-slate-400" />
          )}
        </Button>
      </div>
    </div>
  );
}
