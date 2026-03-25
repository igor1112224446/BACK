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
