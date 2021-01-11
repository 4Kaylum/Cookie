CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30)
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);


CREATE TABLE IF NOT EXISTS guild_cookie_prefixes(
    guild_id BIGINT PRIMARY KEY,
    adjective1 VARCHAR(50) NOT NULL,
    adjective2 VARCHAR(50)
);


CREATE TABLE IF NOT EXISTS user_cookies(
    user_id BIGINT,
    cookie_guild_id BIGINT,
    amount INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, cookie_guild_id)
);
