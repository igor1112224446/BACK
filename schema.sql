create table if not exists bot_users (
    id integer primary key,
    telegram_user_id bigint not null unique,
    username varchar(255),
    first_name varchar(255),
    last_name varchar(255),
    phone varchar(50),
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

create table if not exists bot_conversations (
    id integer primary key,
    bot_user_id integer not null references bot_users(id),
    state varchar(100),
    is_open boolean default true,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

create table if not exists bot_messages (
    id integer primary key,
    conversation_id integer not null references bot_conversations(id),
    direction varchar(20) not null,
    message_text text,
    telegram_message_id integer,
    created_at timestamp default current_timestamp
);

create table if not exists user_requests (
    id integer primary key,
    bot_user_id integer not null references bot_users(id),
    role varchar(20) not null,
    from_city varchar(255) not null,
    to_city varchar(255) not null,
    travel_date date not null,
    weight_kg numeric(10,2) not null,
    description text,
    photo_file_id varchar(500),
    photo_unique_id varchar(500),
    raw_payload text,
    status varchar(20) default 'pending',
    created_at timestamp default current_timestamp,
    matched_at timestamp
);

create table if not exists parsed_offers (
    id integer primary key,
    role varchar(20) not null,
    source_name varchar(100) not null,
    source_offer_id varchar(255) not null,
    from_city varchar(255) not null,
    to_city varchar(255) not null,
    travel_date date not null,
    weight_kg numeric(10,2) not null,
    description text,
    handoff_time_text varchar(255),
    handoff_location varchar(255),
    payment_instructions text,
    internal_contact_ref varchar(255),
    raw_payload text,
    is_active boolean default true,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp,
    constraint uq_source_offer unique (source_name, source_offer_id)
);

create table if not exists matches (
    id integer primary key,
    request_id integer not null references user_requests(id),
    offer_id integer not null references parsed_offers(id),
    status varchar(20) default 'matched',
    message_sent boolean default false,
    created_at timestamp default current_timestamp
);

create table if not exists form_applications (
    id integer primary key,
    retailer_name varchar(255) not null,
    form_url varchar(1000) not null,
    form_name varchar(255),
    raw_payload text,
    status varchar(20) default 'pending',
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

create table if not exists form_field_mappings (
    id integer primary key,
    application_id integer not null references form_applications(id),
    field_name varchar(255) not null,
    field_type varchar(50) not null,
    product_field varchar(255) not null,
    xpath varchar(1000),
    css_selector varchar(1000),
    required boolean default false,
    created_at timestamp default current_timestamp
);

create table if not exists form_submissions (
    id integer primary key,
    application_id integer not null references form_applications(id),
    product_data text not null,
    filled_data text,
    status varchar(20) default 'pending',
    error_message text,
    created_at timestamp default current_timestamp,
    submitted_at timestamp
);

create index if not exists idx_form_applications_retailer on form_applications(retailer_name);
create index if not exists idx_form_applications_status on form_applications(status);
create index if not exists idx_form_field_mappings_application on form_field_mappings(application_id);
create index if not exists idx_form_submissions_application on form_submissions(application_id);
create index if not exists idx_form_submissions_status on form_submissions(status);
