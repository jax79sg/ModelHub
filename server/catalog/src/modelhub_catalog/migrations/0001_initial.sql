-- The Catalog's tables (functional design: entities of the catalog unit).
create extension if not exists pg_trgm;

create table models (
    model_key         text primary key,            -- the model id in lower case (rule BR1.10)
    model_id          text not null,               -- as first imported
    first_imported_at timestamptz not null
);

create table model_versions (
    model_key          text not null references models(model_key),
    commit             text not null check (commit ~ '^[0-9a-f]{40}$'),
    state              text not null default 'imported' check (state in ('imported', 'removed')),
    captured_at        timestamptz not null,
    license            text,
    language           text[],
    tags               text[],
    task               text,
    library            text,
    parameter_count    bigint check (parameter_count is null or parameter_count >= 0),
    downloads          bigint check (downloads is null or downloads >= 0),
    likes              bigint check (likes is null or likes >= 0),
    size_bytes         bigint check (size_bytes is null or size_bytes >= 0),
    counts_captured_at timestamptz,
    created_at         timestamptz,
    last_modified_at   timestamptz,
    has_readme         boolean not null default false,
    card_text          text,
    record_checksum    text not null,
    record_format      integer not null check (record_format >= 1),
    imported_at        timestamptz not null,       -- of the latest import record
    imported_by_id     text not null,
    imported_by_name   text not null,
    removed_at         timestamptz,
    removed_by         text,
    primary key (model_key, commit),
    check ((removed_at is null) = (removed_by is null))
);

create table version_files (
    model_key   text not null,
    commit      text not null,
    path        text not null,
    size_bytes  bigint not null check (size_bytes >= 0),
    sha256      text check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$'),
    file_type   text,
    safety_scan text,
    downloaded  boolean not null,
    primary key (model_key, commit, path),
    foreign key (model_key, commit) references model_versions(model_key, commit)
);

create table refs (
    model_key text not null references models(model_key),
    kind      text not null check (kind in ('branch', 'tag')),
    name      text not null,
    commit    text not null,
    primary key (model_key, kind, name)
);

-- documents are kept in their own table so the list never touches them (rule BR1.8, NFR2.2)
create table documents (
    model_key      text not null,
    commit         text not null,
    kind           text not null check (kind in ('readme', 'readme_local', 'picture', 'response',
                       'manifest', 'bundle_description', 'bundle_signature', 'licence')),
    name           text not null,
    content_type   text not null,
    size_bytes     bigint not null check (size_bytes >= 0 and size_bytes <= 16777216),
    sha256         text not null,
    content        bytea,                           -- null once the version is removed (BR1.12)
    picture_status text check (picture_status is null or picture_status in ('stored', 'unfetched')),
    primary key (model_key, commit, kind, name),
    foreign key (model_key, commit) references model_versions(model_key, commit)
);

create table import_records (
    record_id               uuid primary key,
    model_key               text not null,
    model_id                text not null,
    commit                  text not null,
    imported_by_id          text not null,
    imported_by_name        text not null,
    imported_at             timestamptz not null,
    computer                text not null,
    bundle_name             text not null,
    bundle_sha256           text not null,
    signing_key_fingerprint text not null,
    tool_version            text not null,
    check_results           jsonb not null,
    outcome                 text not null check (outcome in ('imported', 'repaired', 'skipped'))
);
create index import_records_by_time on import_records (imported_at desc);
create index import_records_by_model on import_records (model_key, imported_at desc);
create index import_records_by_person on import_records (imported_by_id, imported_at desc);

-- one narrow row per model, written in the same transaction as the version (rule BR1.7)
create table model_summary (
    model_key        text primary key references models(model_key),
    model_id         text not null,
    latest_commit    text not null,
    state            text not null check (state in ('imported', 'removed')),
    task             text,
    library          text,
    license          text,
    language         text[],
    parameter_count  bigint,
    downloads        bigint,
    likes            bigint,
    last_modified_at timestamptz,
    created_at       timestamptz,
    imported_at      timestamptz not null,
    imported_by_id   text not null,
    imported_by_name text not null,
    tags             text[],
    ids_text         text not null,                  -- model id and tags, for parts-of-word search
    search_vector    tsvector
);
create index summary_downloads on model_summary (downloads desc nulls last, model_key);
create index summary_likes on model_summary (likes desc nulls last, model_key);
create index summary_last_modified on model_summary (last_modified_at desc nulls last, model_key);
create index summary_created on model_summary (created_at desc nulls last, model_key);
create index summary_imported on model_summary (imported_at desc, model_key);
create index summary_name on model_summary (model_key);
create index summary_task on model_summary (task);
create index summary_library on model_summary (library);
create index summary_license on model_summary (license);
create index summary_language on model_summary using gin (language);
create index summary_imported_by on model_summary (imported_by_id);
create index summary_search on model_summary using gin (search_vector);
create index summary_ids_trgm on model_summary using gin (ids_text gin_trgm_ops);

create table personal_tokens (
    token_id      text primary key,
    owner_id      text not null,
    owner_name    text not null,
    name          text not null check (char_length(name) between 1 and 60),
    prefix        text not null,
    value_hash    text not null unique,
    scope         text not null default 'import' check (scope = 'import'),
    created_at    timestamptz not null,
    expires_at    timestamptz not null,
    last_used_at  timestamptz,
    revoked_at    timestamptz,
    revoked_by    text
);
create index tokens_by_owner on personal_tokens (owner_id, created_at desc);

create table catalog_settings (
    key        text primary key check (key in ('token_lifetime_days')),
    value      integer not null check (value between 1 and 365),
    changed_by text,
    changed_at timestamptz
);
insert into catalog_settings (key, value) values ('token_lifetime_days', 90);
