-- Replace the IDs/names below with your real HeyReach LinkedIn account IDs.
-- Adding more profiles later requires only another row here.

insert into leadgen_stats.tracked_accounts (account_id, account_name, active)
values
  (111111, 'Account 1', true),
  (222222, 'Account 2', true),
  (333333, 'Account 3', true)
on conflict (account_id) do update set
  account_name = excluded.account_name,
  active = excluded.active,
  updated_at = now();
