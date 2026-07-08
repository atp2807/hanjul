-- 001_initial.sql — hanjul 전체 스키마 베이스라인 (alembic 폐기 후 신규 raw-SQL 체계)
--
-- 2026-07-08: alembic은 사용자가 여러 프로젝트에 걸쳐 반복 금지해온 도구인데 hanjul에서
-- 과거 세션이 무시하고 채택해 CLAUDE.md에 "컨벤션"으로 박아넣었던 것 — 정정(lr-7b3a0a62,
-- no-alembic-rule.md). 런칭 전이라 0001~0029 alembic 이력을 재현하지 않고 "지금 상태"를
-- 그대로 001로 확정(사용자 결정, 2026-07-08).
--
-- 이 파일만 예외적으로 완전 멱등(CREATE ... IF NOT EXISTS, 제약은 DO $$ EXCEPTION 무시) —
-- 이미 alembic으로 0025까지 적용된 운영 RDS와 완전 빈 신규 DB(로컬/e2e) 양쪽에 안전하게
-- 적용돼야 하기 때문. 002번부터는 migrate.py의 migration_history 추적이 유일한 가드이므로
-- 해드림처럼 평범한 CREATE TABLE(비-멱등)로 작성해도 된다 — 이 001이 "깨끗한 시작점"이 됨.
--
-- 운영 RDS는 verified_tier_cd(usr.account)·woncheon_reported_ts(bill.payout)만 없는
-- 상태(0025까지 적용) — 나머지는 이미 존재해 CREATE TABLE IF NOT EXISTS가 스킵됨. 혹시
-- 이보다 더 오래된 스냅샷에 적용될 경우를 대비해 ADD COLUMN IF NOT EXISTS도 명시.

--
--

--
-- Name: bill; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS bill;

--
-- Name: commu; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS commu;

--
-- Name: dist; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS dist;

--
-- Name: doc; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS doc;

--
-- Name: ms; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS ms;

--
-- Name: potato; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS potato;

--
-- Name: pub; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS pub;

--
-- Name: usr; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS usr;

--
-- Name: bank_account; Type: TABLE; Schema: bill; Owner: -
--

CREATE TABLE IF NOT EXISTS bill.bank_account (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    holder_name character varying(100) NOT NULL,
    bank_cd character varying(20) NOT NULL,
    account_no_enc character varying(255) NOT NULL,
    account_no_masked character varying(50) NOT NULL,
    primary_yn boolean DEFAULT true NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    updated_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: book_order; Type: TABLE; Schema: bill; Owner: -
--

CREATE TABLE IF NOT EXISTS bill.book_order (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    buyer_account_id uuid NOT NULL,
    amount_amt numeric(15,0) NOT NULL,
    channel_cd character varying(20) DEFAULT 'SELF'::character varying NOT NULL,
    status_cd character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    pg_provider_cd character varying(20),
    pg_tx_id character varying(255),
    created_ts timestamp with time zone NOT NULL,
    paid_ts timestamp with time zone,
    refunded_ts timestamp with time zone,
    withdrawal_consent_ts timestamp with time zone
);

--
-- Name: payout; Type: TABLE; Schema: bill; Owner: -
--

CREATE TABLE IF NOT EXISTS bill.payout (
    id uuid NOT NULL,
    author_id uuid NOT NULL,
    status_cd character varying(20) DEFAULT 'REQUESTED'::character varying NOT NULL,
    gross_amt numeric(15,0) NOT NULL,
    withholding_amt numeric(15,0) NOT NULL,
    net_amt numeric(15,0) NOT NULL,
    holder_name character varying(100),
    bank_cd character varying(20),
    account_no_masked character varying(50),
    requested_ts timestamp with time zone DEFAULT now() NOT NULL,
    approved_ts timestamp with time zone,
    paid_ts timestamp with time zone,
    approved_by uuid,
    memo character varying(500),
    woncheon_reported_ts timestamp with time zone
);

--
-- Name: settlement; Type: TABLE; Schema: bill; Owner: -
--

CREATE TABLE IF NOT EXISTS bill.settlement (
    id uuid NOT NULL,
    order_id uuid NOT NULL,
    channel_cd character varying(20) NOT NULL,
    gross_amt numeric(15,0) NOT NULL,
    platform_fee_amt numeric(15,0) NOT NULL,
    withholding_amt numeric(15,0) NOT NULL,
    payout_amt numeric(15,0) NOT NULL,
    created_ts timestamp with time zone NOT NULL,
    payout_id uuid
);

--
-- Name: withholding_subject; Type: TABLE; Schema: bill; Owner: -
--

CREATE TABLE IF NOT EXISTS bill.withholding_subject (
    id uuid NOT NULL,
    payout_id uuid NOT NULL,
    resident_no_enc character varying(255) NOT NULL,
    income_type_cd character varying(20) NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: follow; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.follow (
    id uuid NOT NULL,
    follower_id uuid NOT NULL,
    author_id uuid NOT NULL,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: notification; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.notification (
    id uuid NOT NULL,
    recipient_id uuid NOT NULL,
    kind_cd character varying(20) NOT NULL,
    book_id uuid,
    title text,
    read_yn boolean DEFAULT false NOT NULL,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: report; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.report (
    id uuid NOT NULL,
    reporter_id uuid,
    target_type_cd character varying(20) NOT NULL,
    target_id uuid NOT NULL,
    reason text NOT NULL,
    status_cd character varying(20) DEFAULT 'OPEN'::character varying NOT NULL,
    resolution text,
    resolved_by uuid,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    resolved_ts timestamp with time zone
);

--
-- Name: review; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.review (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    account_id uuid NOT NULL,
    rating integer NOT NULL,
    body text,
    created_ts timestamp with time zone NOT NULL,
    updated_ts timestamp with time zone,
    source_cd character varying(20) DEFAULT 'PURCHASE'::character varying NOT NULL
);

--
-- Name: review_application; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.review_application (
    id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    applicant_id uuid NOT NULL,
    status_cd character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    assigned_ts timestamp with time zone,
    deadline_ts timestamp with time zone,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: review_campaign; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.review_campaign (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    author_id uuid NOT NULL,
    slots integer NOT NULL,
    filled integer DEFAULT 0 NOT NULL,
    review_days integer DEFAULT 7 NOT NULL,
    min_chars integer DEFAULT 0 NOT NULL,
    status_cd character varying(20) DEFAULT 'OPEN'::character varying NOT NULL,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: reviewer_block; Type: TABLE; Schema: commu; Owner: -
--

CREATE TABLE IF NOT EXISTS commu.reviewer_block (
    account_id uuid NOT NULL,
    blocked_until_ts timestamp with time zone NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    updated_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: distribution; Type: TABLE; Schema: dist; Owner: -
--

CREATE TABLE IF NOT EXISTS dist.distribution (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    channel_cd character varying(20) NOT NULL,
    status_cd character varying(20) NOT NULL,
    message text,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: document; Type: TABLE; Schema: doc; Owner: -
--

CREATE TABLE IF NOT EXISTS doc.document (
    id uuid NOT NULL,
    title text DEFAULT ''::text NOT NULL,
    format_cd text DEFAULT ''::text NOT NULL,
    html text NOT NULL,
    source_hash text,
    owner_id uuid,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    updated_ts timestamp with time zone DEFAULT now() NOT NULL,
    deleted_ts timestamp with time zone
);

--
-- Name: share_link; Type: TABLE; Schema: doc; Owner: -
--

CREATE TABLE IF NOT EXISTS doc.share_link (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    token text NOT NULL,
    capability_cd text NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    revoked_ts timestamp with time zone
);

--
-- Name: manuscript_book; Type: TABLE; Schema: ms; Owner: -
--

CREATE TABLE IF NOT EXISTS ms.manuscript_book (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    sync_key uuid NOT NULL,
    title text NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL,
    updated_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: manuscript_revision; Type: TABLE; Schema: ms; Owner: -
--

CREATE TABLE IF NOT EXISTS ms.manuscript_revision (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    chapter_key text NOT NULL,
    chapter_title text NOT NULL,
    html text NOT NULL,
    content_hash text NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: audit_log; Type: TABLE; Schema: potato; Owner: -
--

CREATE TABLE IF NOT EXISTS potato.audit_log (
    id uuid NOT NULL,
    operator_id uuid,
    action character varying(40) NOT NULL,
    entity_type character varying(40) NOT NULL,
    entity_id uuid,
    detail jsonb,
    ip character varying(64),
    created_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: operator; Type: TABLE; Schema: potato; Owner: -
--

CREATE TABLE IF NOT EXISTS potato.operator (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    password_hash character varying(255) NOT NULL,
    name character varying(200) NOT NULL,
    role_cd character varying(20) DEFAULT 'OPERATOR'::character varying NOT NULL,
    active_yn boolean DEFAULT true NOT NULL,
    created_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: block; Type: TABLE; Schema: pub; Owner: -
--

CREATE TABLE IF NOT EXISTS pub.block (
    id uuid NOT NULL,
    chapter_id uuid NOT NULL,
    order_no integer DEFAULT 0 NOT NULL,
    block_type_cd character varying(10) DEFAULT 'P'::character varying NOT NULL,
    html text DEFAULT ''::text NOT NULL,
    created_ts timestamp with time zone NOT NULL,
    updated_ts timestamp with time zone NOT NULL
);

--
-- Name: book; Type: TABLE; Schema: pub; Owner: -
--

CREATE TABLE IF NOT EXISTS pub.book (
    id uuid NOT NULL,
    title character varying(500) NOT NULL,
    subtitle character varying(500),
    kind_cd character varying(20) DEFAULT 'BOOK'::character varying NOT NULL,
    language_cd character varying(10) DEFAULT 'ko'::character varying NOT NULL,
    status_cd character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    cover_url character varying(1000),
    isbn character varying(20),
    author_id uuid,
    created_ts timestamp with time zone NOT NULL,
    updated_ts timestamp with time zone NOT NULL,
    price_amt numeric(15,0),
    published_ts timestamp with time zone,
    scheduled_publish_ts timestamp with time zone,
    description text,
    category_cd character varying(40),
    preview_block_cnt integer DEFAULT 3 NOT NULL,
    discount_amt numeric(15,0),
    discount_until_ts timestamp with time zone,
    blocked_ts timestamp with time zone,
    content_rating_cd character varying(10) DEFAULT 'ALL'::character varying NOT NULL,
    content_rating_detail_json jsonb
);

--
-- Name: chapter; Type: TABLE; Schema: pub; Owner: -
--

CREATE TABLE IF NOT EXISTS pub.chapter (
    id uuid NOT NULL,
    book_id uuid NOT NULL,
    title character varying(500),
    order_no integer DEFAULT 0 NOT NULL,
    created_ts timestamp with time zone NOT NULL,
    updated_ts timestamp with time zone NOT NULL
);

--
-- Name: account; Type: TABLE; Schema: usr; Owner: -
--

CREATE TABLE IF NOT EXISTS usr.account (
    id uuid NOT NULL,
    email character varying(320),
    display_name character varying(200),
    role_cd character varying(20) DEFAULT 'READER'::character varying NOT NULL,
    status_cd character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_ts timestamp with time zone NOT NULL,
    updated_ts timestamp with time zone NOT NULL,
    bio text,
    verified_tier_cd character varying(10) DEFAULT 'ALL'::character varying NOT NULL
);

--
-- Name: age_verification_request; Type: TABLE; Schema: usr; Owner: -
--

CREATE TABLE IF NOT EXISTS usr.age_verification_request (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    id_photo_key character varying(255),
    status_cd character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    reviewed_by uuid,
    reviewed_ts timestamp with time zone,
    created_ts timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: credential; Type: TABLE; Schema: usr; Owner: -
--

CREATE TABLE IF NOT EXISTS usr.credential (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    provider_cd character varying(20) NOT NULL,
    provider_user_id character varying(255) NOT NULL,
    created_ts timestamp with time zone NOT NULL
);

--
-- Name: bank_account bank_account_pkey; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.bank_account
    ADD CONSTRAINT bank_account_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: book_order book_order_pkey; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.book_order
    ADD CONSTRAINT book_order_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: payout payout_pkey; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.payout
    ADD CONSTRAINT payout_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: settlement settlement_order_id_key; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.settlement
    ADD CONSTRAINT settlement_order_id_key UNIQUE (order_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: settlement settlement_pkey; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.settlement
    ADD CONSTRAINT settlement_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: withholding_subject withholding_subject_pkey; Type: CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.withholding_subject
    ADD CONSTRAINT withholding_subject_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: follow follow_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.follow
    ADD CONSTRAINT follow_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: report report_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.report
    ADD CONSTRAINT report_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_application review_application_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_application
    ADD CONSTRAINT review_application_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_campaign review_campaign_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_campaign
    ADD CONSTRAINT review_campaign_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review review_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review
    ADD CONSTRAINT review_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: reviewer_block reviewer_block_pkey; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.reviewer_block
    ADD CONSTRAINT reviewer_block_pkey PRIMARY KEY (account_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_application uq_application_campaign_applicant; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_application
    ADD CONSTRAINT uq_application_campaign_applicant UNIQUE (campaign_id, applicant_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: follow uq_follow_pair; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.follow
    ADD CONSTRAINT uq_follow_pair UNIQUE (follower_id, author_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: notification uq_notification_recipient_book_kind; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.notification
    ADD CONSTRAINT uq_notification_recipient_book_kind UNIQUE (recipient_id, book_id, kind_cd);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review uq_review_book_account; Type: CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review
    ADD CONSTRAINT uq_review_book_account UNIQUE (book_id, account_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: distribution distribution_pkey; Type: CONSTRAINT; Schema: dist; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY dist.distribution
    ADD CONSTRAINT distribution_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: document document_pkey; Type: CONSTRAINT; Schema: doc; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY doc.document
    ADD CONSTRAINT document_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: share_link share_link_pkey; Type: CONSTRAINT; Schema: doc; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY doc.share_link
    ADD CONSTRAINT share_link_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: share_link share_link_token_key; Type: CONSTRAINT; Schema: doc; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY doc.share_link
    ADD CONSTRAINT share_link_token_key UNIQUE (token);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: manuscript_book manuscript_book_pkey; Type: CONSTRAINT; Schema: ms; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY ms.manuscript_book
    ADD CONSTRAINT manuscript_book_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: manuscript_book manuscript_book_sync_key_key; Type: CONSTRAINT; Schema: ms; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY ms.manuscript_book
    ADD CONSTRAINT manuscript_book_sync_key_key UNIQUE (sync_key);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: manuscript_revision manuscript_revision_pkey; Type: CONSTRAINT; Schema: ms; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY ms.manuscript_revision
    ADD CONSTRAINT manuscript_revision_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: potato; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY potato.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: operator operator_pkey; Type: CONSTRAINT; Schema: potato; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY potato.operator
    ADD CONSTRAINT operator_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: operator uq_operator_email; Type: CONSTRAINT; Schema: potato; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY potato.operator
    ADD CONSTRAINT uq_operator_email UNIQUE (email);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: block block_pkey; Type: CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.block
    ADD CONSTRAINT block_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: book book_pkey; Type: CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.book
    ADD CONSTRAINT book_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: chapter chapter_pkey; Type: CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.chapter
    ADD CONSTRAINT chapter_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: account account_email_key; Type: CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.account
    ADD CONSTRAINT account_email_key UNIQUE (email);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: account account_pkey; Type: CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: age_verification_request age_verification_request_pkey; Type: CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.age_verification_request
    ADD CONSTRAINT age_verification_request_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: credential credential_pkey; Type: CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.credential
    ADD CONSTRAINT credential_pkey PRIMARY KEY (id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: credential uq_credential_provider_user; Type: CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.credential
    ADD CONSTRAINT uq_credential_provider_user UNIQUE (provider_cd, provider_user_id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: ix_bank_account_owner; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_bank_account_owner ON bill.bank_account USING btree (account_id);

--
-- Name: ix_bill_order_book; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_bill_order_book ON bill.book_order USING btree (book_id);

--
-- Name: ix_bill_order_buyer; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_bill_order_buyer ON bill.book_order USING btree (buyer_account_id);

--
-- Name: ix_payout_author; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_payout_author ON bill.payout USING btree (author_id);

--
-- Name: ix_payout_status; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_payout_status ON bill.payout USING btree (status_cd);

--
-- Name: ix_settlement_payout; Type: INDEX; Schema: bill; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_settlement_payout ON bill.settlement USING btree (payout_id);

--
-- Name: ix_withholding_subject_payout; Type: INDEX; Schema: bill; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS ix_withholding_subject_payout ON bill.withholding_subject USING btree (payout_id);

--
-- Name: ix_commu_application_applicant; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_application_applicant ON commu.review_application USING btree (applicant_id);

--
-- Name: ix_commu_application_campaign; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_application_campaign ON commu.review_application USING btree (campaign_id);

--
-- Name: ix_commu_campaign_status; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_campaign_status ON commu.review_campaign USING btree (status_cd);

--
-- Name: ix_commu_follow_author; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_follow_author ON commu.follow USING btree (author_id);

--
-- Name: ix_commu_notification_recipient; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_notification_recipient ON commu.notification USING btree (recipient_id);

--
-- Name: ix_commu_review_book; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_commu_review_book ON commu.review USING btree (book_id);

--
-- Name: ix_report_status; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_report_status ON commu.report USING btree (status_cd);

--
-- Name: ix_report_target; Type: INDEX; Schema: commu; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_report_target ON commu.report USING btree (target_type_cd, target_id);

--
-- Name: ix_dist_distribution_book; Type: INDEX; Schema: dist; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_dist_distribution_book ON dist.distribution USING btree (book_id);

--
-- Name: ix_document_active; Type: INDEX; Schema: doc; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_document_active ON doc.document USING btree (created_ts DESC) WHERE (deleted_ts IS NULL);

--
-- Name: ix_document_owner; Type: INDEX; Schema: doc; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_document_owner ON doc.document USING btree (owner_id) WHERE (owner_id IS NOT NULL);

--
-- Name: ix_share_link_document; Type: INDEX; Schema: doc; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_share_link_document ON doc.share_link USING btree (document_id, created_ts DESC);

--
-- Name: ix_share_link_token; Type: INDEX; Schema: doc; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_share_link_token ON doc.share_link USING btree (token);

--
-- Name: ix_manuscript_book_account; Type: INDEX; Schema: ms; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_manuscript_book_account ON ms.manuscript_book USING btree (account_id);

--
-- Name: ix_manuscript_revision_book_chapter; Type: INDEX; Schema: ms; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_manuscript_revision_book_chapter ON ms.manuscript_revision USING btree (book_id, chapter_key, created_ts DESC);

--
-- Name: ix_audit_log_entity; Type: INDEX; Schema: potato; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON potato.audit_log USING btree (entity_type, entity_id);

--
-- Name: ix_audit_log_operator; Type: INDEX; Schema: potato; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_audit_log_operator ON potato.audit_log USING btree (operator_id);

--
-- Name: ix_pub_block_chapter_id; Type: INDEX; Schema: pub; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_pub_block_chapter_id ON pub.block USING btree (chapter_id);

--
-- Name: ix_pub_book_scheduled; Type: INDEX; Schema: pub; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_pub_book_scheduled ON pub.book USING btree (scheduled_publish_ts) WHERE (scheduled_publish_ts IS NOT NULL);

--
-- Name: ix_pub_book_status; Type: INDEX; Schema: pub; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_pub_book_status ON pub.book USING btree (status_cd);

--
-- Name: ix_pub_chapter_book_id; Type: INDEX; Schema: pub; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_pub_chapter_book_id ON pub.chapter USING btree (book_id);

--
-- Name: ix_age_verification_request_account; Type: INDEX; Schema: usr; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_age_verification_request_account ON usr.age_verification_request USING btree (account_id);

--
-- Name: ix_age_verification_request_status; Type: INDEX; Schema: usr; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_age_verification_request_status ON usr.age_verification_request USING btree (status_cd);

--
-- Name: ix_usr_credential_account_id; Type: INDEX; Schema: usr; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_usr_credential_account_id ON usr.credential USING btree (account_id);

--
-- Name: bank_account bank_account_account_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.bank_account
    ADD CONSTRAINT bank_account_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: book_order book_order_book_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.book_order
    ADD CONSTRAINT book_order_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE RESTRICT;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: book_order book_order_buyer_account_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.book_order
    ADD CONSTRAINT book_order_buyer_account_id_fkey FOREIGN KEY (buyer_account_id) REFERENCES usr.account(id) ON DELETE RESTRICT;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: payout payout_approved_by_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.payout
    ADD CONSTRAINT payout_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES potato.operator(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: payout payout_author_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.payout
    ADD CONSTRAINT payout_author_id_fkey FOREIGN KEY (author_id) REFERENCES usr.account(id) ON DELETE RESTRICT;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: settlement settlement_order_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.settlement
    ADD CONSTRAINT settlement_order_id_fkey FOREIGN KEY (order_id) REFERENCES bill.book_order(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: settlement settlement_payout_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.settlement
    ADD CONSTRAINT settlement_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES bill.payout(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: withholding_subject withholding_subject_payout_id_fkey; Type: FK CONSTRAINT; Schema: bill; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY bill.withholding_subject
    ADD CONSTRAINT withholding_subject_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES bill.payout(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: follow follow_author_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.follow
    ADD CONSTRAINT follow_author_id_fkey FOREIGN KEY (author_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: follow follow_follower_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.follow
    ADD CONSTRAINT follow_follower_id_fkey FOREIGN KEY (follower_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: notification notification_book_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.notification
    ADD CONSTRAINT notification_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: notification notification_recipient_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.notification
    ADD CONSTRAINT notification_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: report report_reporter_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.report
    ADD CONSTRAINT report_reporter_id_fkey FOREIGN KEY (reporter_id) REFERENCES usr.account(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: report report_resolved_by_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.report
    ADD CONSTRAINT report_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES potato.operator(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review review_account_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review
    ADD CONSTRAINT review_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_application review_application_applicant_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_application
    ADD CONSTRAINT review_application_applicant_id_fkey FOREIGN KEY (applicant_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_application review_application_campaign_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_application
    ADD CONSTRAINT review_application_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commu.review_campaign(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review review_book_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review
    ADD CONSTRAINT review_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_campaign review_campaign_author_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_campaign
    ADD CONSTRAINT review_campaign_author_id_fkey FOREIGN KEY (author_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: review_campaign review_campaign_book_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.review_campaign
    ADD CONSTRAINT review_campaign_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: reviewer_block reviewer_block_account_id_fkey; Type: FK CONSTRAINT; Schema: commu; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY commu.reviewer_block
    ADD CONSTRAINT reviewer_block_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: distribution distribution_book_id_fkey; Type: FK CONSTRAINT; Schema: dist; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY dist.distribution
    ADD CONSTRAINT distribution_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: document document_owner_id_fkey; Type: FK CONSTRAINT; Schema: doc; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY doc.document
    ADD CONSTRAINT document_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES usr.account(id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: share_link share_link_document_id_fkey; Type: FK CONSTRAINT; Schema: doc; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY doc.share_link
    ADD CONSTRAINT share_link_document_id_fkey FOREIGN KEY (document_id) REFERENCES doc.document(id);
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: manuscript_book manuscript_book_account_id_fkey; Type: FK CONSTRAINT; Schema: ms; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY ms.manuscript_book
    ADD CONSTRAINT manuscript_book_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: manuscript_revision manuscript_revision_book_id_fkey; Type: FK CONSTRAINT; Schema: ms; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY ms.manuscript_revision
    ADD CONSTRAINT manuscript_revision_book_id_fkey FOREIGN KEY (book_id) REFERENCES ms.manuscript_book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: audit_log audit_log_operator_id_fkey; Type: FK CONSTRAINT; Schema: potato; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY potato.audit_log
    ADD CONSTRAINT audit_log_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES potato.operator(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: block block_chapter_id_fkey; Type: FK CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.block
    ADD CONSTRAINT block_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES pub.chapter(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: chapter chapter_book_id_fkey; Type: FK CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.chapter
    ADD CONSTRAINT chapter_book_id_fkey FOREIGN KEY (book_id) REFERENCES pub.book(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: book fk_book_author_account; Type: FK CONSTRAINT; Schema: pub; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY pub.book
    ADD CONSTRAINT fk_book_author_account FOREIGN KEY (author_id) REFERENCES usr.account(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: age_verification_request age_verification_request_account_id_fkey; Type: FK CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.age_verification_request
    ADD CONSTRAINT age_verification_request_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: age_verification_request age_verification_request_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.age_verification_request
    ADD CONSTRAINT age_verification_request_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES potato.operator(id) ON DELETE SET NULL;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
-- Name: credential credential_account_id_fkey; Type: FK CONSTRAINT; Schema: usr; Owner: -
--

DO $$ BEGIN
    ALTER TABLE ONLY usr.credential
    ADD CONSTRAINT credential_account_id_fkey FOREIGN KEY (account_id) REFERENCES usr.account(id) ON DELETE CASCADE;
EXCEPTION
        WHEN duplicate_object THEN NULL;
        WHEN duplicate_table THEN NULL;
        WHEN invalid_table_definition THEN NULL;
END $$;

--
--

-- 신규 컬럼 안전망 (기존 테이블에 CREATE TABLE IF NOT EXISTS가 스킵될 경우 대비)
ALTER TABLE pub.book ADD COLUMN IF NOT EXISTS content_rating_cd character varying(10) DEFAULT 'ALL'::character varying NOT NULL;
ALTER TABLE pub.book ADD COLUMN IF NOT EXISTS content_rating_detail_json jsonb;
ALTER TABLE usr.account ADD COLUMN IF NOT EXISTS verified_tier_cd character varying(10) DEFAULT 'ALL'::character varying NOT NULL;
ALTER TABLE bill.payout ADD COLUMN IF NOT EXISTS woncheon_reported_ts timestamp with time zone;

-- alembic 폐기 — 옛 추적 테이블 정리(있으면 제거, 없으면 무시)
DROP TABLE IF EXISTS public.alembic_version;
