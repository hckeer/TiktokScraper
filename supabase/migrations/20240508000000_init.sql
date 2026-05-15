CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tiktok_username TEXT NOT NULL,
  temporal_workflow_id TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'connecting',
  started_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ,
  total_comments INT DEFAULT 0,
  total_numbers INT DEFAULT 0,
  client_ip TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE extracted_numbers (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  phone_number TEXT NOT NULL,
  source_comment TEXT,
  extracted_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_extracted_numbers_session ON extracted_numbers(session_id);
CREATE INDEX idx_sessions_status ON sessions(status);
