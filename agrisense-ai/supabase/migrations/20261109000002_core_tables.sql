-- AgriSense AI
-- 2 of 4. Run after 20261109000001_extensions.sql.
--
-- Timestamps are stored in UTC. Convert to Asia/Kolkata in the application.
-- Row level security is enabled and no anon or authenticated policies are added.
-- The backend service-role key bypasses RLS. Do not expose that key to the frontend.
-- There are no user, role, or tenant tables.

-- ---------------------------------------------------------------------------
-- locations
-- ---------------------------------------------------------------------------

create table public.locations (
  id uuid primary key default extensions.gen_random_uuid(),
  name text not null,
  state text not null,
  district text not null,
  latitude numeric(9, 6) not null,
  longitude numeric(9, 6) not null,
  created_at timestamptz not null default now(),
  constraint locations_name_not_blank check (char_length(btrim(name)) > 0),
  constraint locations_state_not_blank check (char_length(btrim(state)) > 0),
  constraint locations_district_not_blank check (char_length(btrim(district)) > 0),
  constraint locations_latitude_range check (latitude >= -90 and latitude <= 90),
  constraint locations_longitude_range check (longitude >= -180 and longitude <= 180)
);

comment on table public.locations is
  'Agricultural locations selected by the internal operator. Coordinates are used for weather retrieval.';

-- ---------------------------------------------------------------------------
-- crop_records
-- ---------------------------------------------------------------------------

create table public.crop_records (
  id uuid primary key default extensions.gen_random_uuid(),
  location_id uuid not null references public.locations (id) on delete restrict,
  crop_name text not null,
  variety text,
  sowing_date date not null,
  expected_harvest_date date,
  growth_stage text not null,
  soil_type text not null,
  soil_ph numeric,
  nitrogen numeric,
  phosphorus numeric,
  potassium numeric,
  irrigation_method text not null,
  observations text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint crop_records_crop_name_not_blank check (char_length(btrim(crop_name)) > 0),
  constraint crop_records_growth_stage_check check (
    growth_stage in (
      'seedling',
      'vegetative',
      'flowering',
      'fruiting',
      'maturity',
      'harvest'
    )
  ),
  constraint crop_records_soil_type_not_blank check (char_length(btrim(soil_type)) > 0),
  constraint crop_records_irrigation_not_blank check (char_length(btrim(irrigation_method)) > 0),
  constraint crop_records_soil_ph_range check (
    soil_ph is null or (soil_ph >= 0 and soil_ph <= 14)
  ),
  constraint crop_records_nitrogen_non_negative check (nitrogen is null or nitrogen >= 0),
  constraint crop_records_phosphorus_non_negative check (phosphorus is null or phosphorus >= 0),
  constraint crop_records_potassium_non_negative check (potassium is null or potassium >= 0),
  constraint crop_records_harvest_after_sowing check (
    expected_harvest_date is null or expected_harvest_date >= sowing_date
  )
);

comment on table public.crop_records is
  'Crop records maintained by the internal operator. NPK values are optional operator inputs, not calculated doses.';

comment on column public.crop_records.growth_stage is
  'One of seedling, vegetative, flowering, fruiting, maturity, harvest.';

-- ---------------------------------------------------------------------------
-- environmental_records
-- ---------------------------------------------------------------------------

create table public.environmental_records (
  id uuid primary key default extensions.gen_random_uuid(),
  location_id uuid not null references public.locations (id) on delete restrict,
  crop_id uuid references public.crop_records (id) on delete set null,
  temperature numeric,
  humidity numeric,
  rainfall numeric,
  precipitation_probability numeric,
  wind_speed numeric,
  soil_moisture numeric,
  soil_ph numeric,
  conditions text,
  source text not null,
  raw_payload jsonb,
  recorded_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint environmental_records_source_not_blank check (char_length(btrim(source)) > 0),
  constraint environmental_records_humidity_range check (
    humidity is null or (humidity >= 0 and humidity <= 100)
  ),
  constraint environmental_records_precip_prob_range check (
    precipitation_probability is null
    or (precipitation_probability >= 0 and precipitation_probability <= 100)
  ),
  constraint environmental_records_rainfall_non_negative check (
    rainfall is null or rainfall >= 0
  ),
  constraint environmental_records_wind_non_negative check (
    wind_speed is null or wind_speed >= 0
  ),
  constraint environmental_records_soil_moisture_non_negative check (
    soil_moisture is null or soil_moisture >= 0
  ),
  constraint environmental_records_soil_ph_range check (
    soil_ph is null or (soil_ph >= 0 and soil_ph <= 14)
  )
);

comment on table public.environmental_records is
  'Weather and soil snapshots. Leave a measurement null when the provider did not return it. Do not store fabricated readings.';

comment on column public.environmental_records.conditions is
  'Provider weather-condition label, such as an Open-Meteo weather code description. Null when unavailable.';

comment on column public.environmental_records.raw_payload is
  'Optional original provider payload kept with the snapshot. Not a substitute for the normalized columns.';

comment on column public.environmental_records.recorded_at is
  'UTC time the observation applies to. Display as Indian Standard Time in the application.';

-- ---------------------------------------------------------------------------
-- advisory_records
-- ---------------------------------------------------------------------------

create table public.advisory_records (
  id uuid primary key default extensions.gen_random_uuid(),
  crop_id uuid references public.crop_records (id) on delete set null,
  location_id uuid references public.locations (id) on delete set null,
  advisory_type text not null,
  input_context jsonb not null default '{}'::jsonb,
  advisory_response jsonb not null default '{}'::jsonb,
  retrieved_sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  constraint advisory_records_type_check check (
    advisory_type in (
      'crop_management',
      'disease_prevention',
      'chatbot',
      'alert_explanation'
    )
  )
);

comment on table public.advisory_records is
  'Historical LLM advisories. retrieved_sources is a snapshot of citations returned at the time and is not a foreign key.';

comment on column public.advisory_records.advisory_type is
  'One of crop_management, disease_prevention, chatbot, alert_explanation.';

-- ---------------------------------------------------------------------------
-- chat_messages
-- ---------------------------------------------------------------------------

create table public.chat_messages (
  id uuid primary key default extensions.gen_random_uuid(),
  conversation_id uuid not null,
  crop_id uuid references public.crop_records (id) on delete set null,
  role text not null,
  message text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint chat_messages_role_check check (role in ('user', 'assistant', 'system')),
  constraint chat_messages_message_not_blank check (char_length(btrim(message)) > 0)
);

comment on table public.chat_messages is
  'Chatbot turns grouped by conversation_id. There is no separate conversations table.';

comment on column public.chat_messages.metadata is
  'Optional context for a turn, such as weather snapshot ids and retrieved knowledge references.';

-- ---------------------------------------------------------------------------
-- alerts
-- ---------------------------------------------------------------------------

create table public.alerts (
  id uuid primary key default extensions.gen_random_uuid(),
  crop_id uuid references public.crop_records (id) on delete set null,
  location_id uuid references public.locations (id) on delete set null,
  title text not null,
  description text not null,
  category text not null,
  severity text not null,
  supporting_context jsonb not null default '{}'::jsonb,
  is_read boolean not null default false,
  created_at timestamptz not null default now(),
  constraint alerts_title_not_blank check (char_length(btrim(title)) > 0),
  constraint alerts_description_not_blank check (char_length(btrim(description)) > 0),
  constraint alerts_category_check check (
    category in (
      'rainfall',
      'temperature',
      'humidity',
      'soil_moisture',
      'disease_symptoms'
    )
  ),
  constraint alerts_severity_check check (
    severity in ('info', 'low', 'moderate', 'high')
  )
);

comment on table public.alerts is
  'Rule-based alert records. Thresholds live in application config and are not scientifically validated disease predictions.';

comment on column public.alerts.category is
  'One of rainfall, temperature, humidity, soil_moisture, disease_symptoms.';

comment on column public.alerts.severity is
  'One of info, low, moderate, high. Descriptive only, not a calibrated probability.';

-- ---------------------------------------------------------------------------
-- updated_at
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger crop_records_set_updated_at
before update on public.crop_records
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- indexes
-- ---------------------------------------------------------------------------

create index locations_state_district_idx
  on public.locations (state, district);

create index locations_name_idx
  on public.locations (name);

create index crop_records_location_id_idx
  on public.crop_records (location_id);

create index crop_records_crop_name_idx
  on public.crop_records (crop_name);

create index crop_records_growth_stage_idx
  on public.crop_records (growth_stage);

create index environmental_records_location_recorded_idx
  on public.environmental_records (location_id, recorded_at desc);

create index environmental_records_crop_recorded_idx
  on public.environmental_records (crop_id, recorded_at desc);

create index advisory_records_crop_id_idx
  on public.advisory_records (crop_id);

create index advisory_records_location_id_idx
  on public.advisory_records (location_id);

create index advisory_records_type_created_idx
  on public.advisory_records (advisory_type, created_at desc);

create index advisory_records_created_idx
  on public.advisory_records (created_at desc);

create index chat_messages_conversation_created_idx
  on public.chat_messages (conversation_id, created_at);

create index alerts_created_idx
  on public.alerts (created_at desc);

create index alerts_crop_id_idx
  on public.alerts (crop_id);

create index alerts_location_id_idx
  on public.alerts (location_id);

create index alerts_unread_idx
  on public.alerts (created_at desc)
  where is_read = false;

-- ---------------------------------------------------------------------------
-- row level security
-- No policies are created. anon and authenticated roles see nothing.
-- The service role, used only by the FastAPI backend, bypasses RLS.
-- ---------------------------------------------------------------------------

alter table public.locations enable row level security;
alter table public.crop_records enable row level security;
alter table public.environmental_records enable row level security;
alter table public.advisory_records enable row level security;
alter table public.chat_messages enable row level security;
alter table public.alerts enable row level security;
