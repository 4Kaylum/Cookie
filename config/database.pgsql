CREATE TABLE guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30)
);


CREATE TABLE guild_cookie_prefixes(
    guild_id BIGINT PRIMARY KEY,
    adjective1 VARCHAR(50) NOT NULL,
    adjective2 VARCHAR(50)
);


CREATE TABLE user_cookies(
    user_id BIGINT,
    cookie_guild_id BIGINT,
    amount INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, cookie_guild_id)
);
