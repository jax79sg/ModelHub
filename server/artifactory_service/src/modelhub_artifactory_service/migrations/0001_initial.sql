-- artifactory-service's own tables, in its own schema (functional design: entities of the unit).

create table import_jobs (
    import_id               text primary key,
    model_id                text not null,
    model_key               text not null,
    commit                  text not null check (commit ~ '^[0-9a-f]{40}$'),
    owner_id                text not null,
    owner_name              text not null,
    bundle_name             text not null,
    bundle_description      text not null,
    bundle_signature        text not null,
    signing_key_fingerprint text not null,
    computer                text not null,
    tool_version            text not null,
    check_results           jsonb,
    plan                    text check (plan in ('skip', 'finish', 'repair', 'full', 'pending')),
    state                   text not null check (state in ('receiving', 'ready', 'verifying',
                                'uploading', 'recording', 'done', 'failed', 'cancelled', 'skipped')),
    outcome                 text check (outcome in ('imported', 'completed', 'skipped', 'failed')),
    piece_count             integer not null check (piece_count >= 1),
    step                    text,
    bytes_done              bigint check (bytes_done is null or bytes_done >= 0),
    bytes_total             bigint check (bytes_total is null or bytes_total >= 0),
    error_code              text,
    error_message           text,
    retryable               boolean,
    created_at              timestamptz not null,
    last_activity_at        timestamptz not null,
    ended_at                timestamptz
);
create index import_jobs_by_state on import_jobs (state);

create table received_pieces (
    import_id  text not null references import_jobs(import_id) on delete cascade,
    index      integer not null check (index between 1 and 999999),
    sha256     text not null,
    size_bytes bigint not null check (size_bytes >= 0),
    consumed   boolean not null default false,
    primary key (import_id, index)
);

-- one import per model at a time (rule BR1.9)
create table model_locks (
    model_key   text primary key,
    import_id   text not null references import_jobs(import_id) on delete cascade,
    acquired_at timestamptz not null
);

create table trusted_keys (
    fingerprint      text primary key,
    key_id           text not null unique,
    public_key       text not null,
    label            text not null check (char_length(label) between 1 and 80),
    added_by_id      text not null,
    added_by_name    text not null,
    added_at         timestamptz not null,
    revoked_at       timestamptz,
    revoked_by_name  text
);

create table retention_settings (
    id              integer primary key check (id = 1),
    retention_days  integer not null check (retention_days between 1 and 3650),
    changed_by_name text,
    changed_at      timestamptz
);
insert into retention_settings (id, retention_days) values (1, 365);

create table retention_decisions (
    decision_id      text primary key,
    model_id         text not null,
    commit           text not null,
    decision         text not null check (decision in ('keep', 'remove')),
    decided_by_id    text not null,
    decided_by_name  text not null,
    decided_at       timestamptz not null,
    outcome          text not null check (outcome in ('done', 'failed', 'files_deleted_not_marked')),
    failure_code     text,
    failure_message  text
);
create index retention_decisions_by_version on retention_decisions (model_id, commit, decided_at desc);
