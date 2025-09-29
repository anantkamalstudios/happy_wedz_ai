CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT
);

CREATE TABLE email_templates (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    template_file TEXT NOT NULL
);

CREATE TABLE email_queue (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    template_id INT REFERENCES email_templates(id),
    context JSONB,
    scheduled_at TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT CHECK (status IN ('pending','sent','failed'))
);

CREATE TABLE email_log (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    template_id INT REFERENCES email_templates(id),
    status TEXT,
    sent_at TIMESTAMP
);

CREATE TABLE user_activity (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    activity_type TEXT,
    metadata JSONB,
    timestamp TIMESTAMP
);
