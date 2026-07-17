-- 1. Tracked sender accounts
select *
from leadgen_stats.tracked_accounts
order by account_name;

-- 2. Last seven days of final metrics
select *
from leadgen_stats.v_daily_metrics
where metric_date >= current_date - 7
order by metric_date desc, account_name;

-- 3. Current-month totals by account
select
  account_id,
  account_name,
  sum(campaign_connections) as campaign_connections,
  sum(manual_connections) as manual_connections,
  sum(automatic_messages) as automatic_messages,
  sum(manual_messages) as manual_messages,
  sum(unknown_connections) as unknown_connections,
  sum(unknown_messages) as unknown_messages
from leadgen_stats.v_daily_metrics
where metric_date >= date_trunc('month', current_date)::date
group by account_id, account_name
order by account_name;

-- 4. Events that still need investigation
select
  account_id,
  event_type,
  attribution,
  count(*) as events
from leadgen_stats.outreach_events
where attribution = 'unknown'
group by account_id, event_type, attribution
order by events desc;

-- 5. Outbound messages with unknown attribution
select
  account_id,
  sent_at,
  lead_profile_url,
  conversation_id,
  message_id,
  body
from leadgen_stats.messages
where direction = 'outbound'
  and attribution = 'unknown'
order by sent_at desc
limit 100;

-- 6. Recent raw payloads for payload-audit/debugging
select
  received_at,
  event_type,
  account_id,
  is_tracked,
  normalized_payload,
  raw_payload
from leadgen_stats.raw_heyreach_events
order by received_at desc
limit 25;

-- 7. Force a rolling recalculation after correcting mappings
select leadgen_stats.refresh_daily_metrics(current_date - 90, current_date);
