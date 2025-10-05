-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Paper Table
-- ========================================
CREATE TABLE IF NOT EXISTS paper (
    id SERIAL PRIMARY KEY,
    paper_id TEXT UNIQUE,
    full_text TEXT,
    author_list TEXT[],
    title TEXT,
    abstract TEXT,
    json_data JSONB,
    embeddings vector(768), -- Adjust dimension as needed (e.g., 768 for BERT, 1536 for OpenAI)
    plot_visualize_x FLOAT,
    plot_visualize_y FLOAT,
    plot_visualize_z FLOAT,
    cluster TEXT, 
    -- relatedby: list of paper IDs (string) that write about this paper in their related works
    _references TEXT[],
    score FLOAT,
    cited_by TEXT[], -- link of list of paper (string) that cite this paper
    html_context TEXT,
    topic TEXT,
    md_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_paper_embeddings ON paper USING ivfflat (embeddings vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_paper_json ON paper USING gin(json_data);
CREATE INDEX IF NOT EXISTS idx_paper_cluster ON paper(cluster);


-- ========================================
-- Key Knowledge Table
-- ========================================
CREATE TABLE IF NOT EXISTS key_knowledge ( -- Single keyword 
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    context TEXT[],
    embedding vector(768), -- Adjust dimension as needed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_key_knowledge_paper_id ON key_knowledge(paper_id);
CREATE INDEX IF NOT EXISTS idx_key_knowledge_embedding ON key_knowledge USING ivfflat (embedding vector_cosine_ops);


-- ========================================
-- Author Table
-- ========================================
CREATE TABLE IF NOT EXISTS author (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_name VARCHAR(255) NOT NULL UNIQUE,
    -- List of paper this author is corresponding author for
    corresponding_of TEXT[],
    -- List of paper this author is writer for
    writing_of TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_author_name ON author(author_name);
CREATE INDEX IF NOT EXISTS idx_author_corresponding ON author USING gin(corresponding_of);
CREATE INDEX IF NOT EXISTS idx_author_writing ON author USING gin(writing_of);


-- ========================================
-- Constraint: Ensure author_list references existing authors
-- ========================================
-- Function to validate that all authors in author_list exist in author table
CREATE OR REPLACE FUNCTION validate_author_list()
RETURNS TRIGGER AS $$
DECLARE
    author_name_var TEXT;
BEGIN
    -- Check each author name in the array
    IF NEW.author_list IS NOT NULL THEN
        FOREACH author_name_var IN ARRAY NEW.author_list
        LOOP
            -- Check if author exists in author table
            IF NOT EXISTS (SELECT 1 FROM author WHERE author_name = author_name_var) THEN
                RAISE EXCEPTION 'Author "%" does not exist in author table', author_name_var;
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to enforce author_list constraint
CREATE TRIGGER validate_paper_author_list
    BEFORE INSERT OR UPDATE ON paper
    FOR EACH ROW
    EXECUTE FUNCTION validate_author_list();


-- ========================================
-- Update timestamp trigger function
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_author_updated_at BEFORE UPDATE ON author
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_updated_at BEFORE UPDATE ON paper
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_key_knowledge_updated_at BEFORE UPDATE ON key_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Helpful Views
-- ========================================

-- View: Papers with their authors (using author_list array)
CREATE OR REPLACE VIEW paper_with_authors AS
SELECT 
    p.id,
    p.paper_id,
    p.title,
    p.abstract,
    p.full_text,
    p.json_data,
    p.plot_visualize_x,
    p.plot_visualize_y,
    p.plot_visualize_z,
    p.cluster,
    p.author_list,
    (
        SELECT json_agg(
            json_build_object(
                'author_id', a.id,
                'author_name', a.author_name
            )
        )
        FROM unnest(p.author_list) AS author_name_item
        JOIN author a ON a.author_name = author_name_item
    ) as authors_details
FROM paper p;

-- View: Papers with their key knowledge
CREATE OR REPLACE VIEW paper_with_key_knowledge AS
SELECT 
    p.id,
    p.paper_id,
    p.title,
    p.full_text,
    json_agg(
        json_build_object(
            'id', kk.id,
            'context', kk.context
        )
    ) as key_knowledge
FROM paper p
LEFT JOIN key_knowledge kk ON p.id = kk.paper_id
GROUP BY p.id, p.paper_id, p.title, p.full_text;

-- ========================================
-- Sample queries (commented out)
-- ========================================

-- Find similar papers by embedding
-- SELECT id, paper_id, title, embeddings <=> '[0.1, 0.2, ...]'::vector AS distance
-- FROM paper
-- ORDER BY distance
-- LIMIT 10;

-- Get paper with all relations
-- SELECT 
--     p.*,
--     (SELECT json_agg(a.author_name) FROM unnest(p.author_list) AS author_name_item JOIN author a ON a.author_name = author_name_item) as authors,
--     (SELECT json_agg(kk.context) FROM key_knowledge kk WHERE kk.paper_id = p.id) as key_knowledge
-- FROM paper p
-- WHERE p.paper_id = 'PMC123456';

-- Find papers by author
-- SELECT p.* 
-- FROM paper p
-- WHERE 'Author Name' = ANY(p.author_list);

-- Get all papers an author wrote
-- SELECT a.author_name, a.writing_of
-- FROM author a
-- WHERE a.author_name = 'Author Name';

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    fiscal_year INTEGER,
    pi_institution TEXT,
    pi_institution_type TEXT,
    project_start_date DATE,
    project_end_date DATE,
    solicitation_funding_source TEXT,
    research_impact_earth_benefit TEXT,
    abstract TEXT,
    raw_text TEXT, -- Combined text from all relevant columns
    summary JSONB, -- Structured summary from LLM (Objective, Methodology, Key Findings, etc.)
    embedding vector(768), -- text-multilingual-embedding-002 embeddings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for projects table
CREATE INDEX IF NOT EXISTS idx_projects_embedding ON projects USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_projects_fiscal_year ON projects(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_projects_institution ON projects(pi_institution);
CREATE INDEX IF NOT EXISTS idx_projects_title ON projects USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_projects_abstract ON projects USING gin(to_tsvector('english', abstract));

-- Analysis Cache Table - Cache LLM Results
CREATE TABLE IF NOT EXISTS analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of paper text
    paper_summary TEXT NOT NULL, -- Original paper summary/abstract
    top_projects JSONB, -- Array of similar projects (project_id, title, similarity_score)
    llm_output JSONB, -- Full structured analysis result
    cache_hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for analysis_cache table
CREATE INDEX IF NOT EXISTS idx_analysis_cache_hash ON analysis_cache(paper_hash);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_created ON analysis_cache(created_at);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_accessed ON analysis_cache(last_accessed);

-- Cost Tracking Table - Monitor API Usage
CREATE TABLE IF NOT EXISTS cost_tracker (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID,
    paper_id TEXT, -- Reference to paper being analyzed
    operation_type VARCHAR(50) NOT NULL, -- 'embedding', 'llm_analysis', 'similarity_search'
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.00,
    cache_hit BOOLEAN DEFAULT FALSE,
    top_k_used INTEGER DEFAULT 0, -- Number of similar projects used
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for cost_tracker table
CREATE INDEX IF NOT EXISTS idx_cost_tracker_operation ON cost_tracker(operation_type);
CREATE INDEX IF NOT EXISTS idx_cost_tracker_created ON cost_tracker(created_at);
CREATE INDEX IF NOT EXISTS idx_cost_tracker_paper_id ON cost_tracker(paper_id);

-- ========================================
-- Paper Analysis Triggers
-- ========================================

-- Update timestamp trigger for projects
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update last_accessed for analysis_cache on cache hits
CREATE OR REPLACE FUNCTION update_cache_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = CURRENT_TIMESTAMP;
    NEW.cache_hit_count = OLD.cache_hit_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_analysis_cache_access
    BEFORE UPDATE ON analysis_cache
    FOR EACH ROW EXECUTE FUNCTION update_cache_access();

-- ========================================
-- Paper Analysis Views
-- ========================================

-- Daily cost summary view
CREATE OR REPLACE VIEW daily_cost_summary AS
SELECT 
    DATE(created_at) as date,
    operation_type,
    COUNT(*) as total_requests,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(cost_usd) as total_cost_usd,
    AVG(response_time_ms) as avg_response_time_ms,
    ROUND(
        (SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)) * 100, 2
    ) as cache_hit_rate_percent
FROM cost_tracker
GROUP BY DATE(created_at), operation_type
ORDER BY date DESC, operation_type;

-- Project statistics view
CREATE OR REPLACE VIEW project_statistics AS
SELECT 
    COUNT(*) as total_projects,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as projects_with_embeddings,
    COUNT(CASE WHEN summary IS NOT NULL THEN 1 END) as projects_with_summaries,
    COUNT(DISTINCT fiscal_year) as unique_fiscal_years,
    COUNT(DISTINCT pi_institution) as unique_institutions,
    MIN(fiscal_year) as earliest_year,
    MAX(fiscal_year) as latest_year
FROM projects;