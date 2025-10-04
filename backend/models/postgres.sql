-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Paper Table
-- ========================================
CREATE TABLE IF NOT EXISTS paper (
    id SERIAL PRIMARY KEY,
    paper_id TEXT UNIQUE NOT NULL,
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
    cited_by TEXT[], -- link of list of paper (string) that cite this paper
    score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_paper_embeddings ON paper USING ivfflat (embeddings vector_cosine_ops);
CREATE INDEX idx_paper_json ON paper USING gin(json_data);
CREATE INDEX idx_paper_cluster ON paper(cluster);


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

CREATE INDEX idx_key_knowledge_paper_id ON key_knowledge(paper_id);
CREATE INDEX idx_key_knowledge_embedding ON key_knowledge USING ivfflat (embedding vector_cosine_ops);


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

CREATE INDEX idx_author_name ON author(author_name);
CREATE INDEX idx_author_corresponding ON author USING gin(corresponding_of);
CREATE INDEX idx_author_writing ON author USING gin(writing_of);


 -- References of a paper to other papers (e.g., related works, citations)


CREATE INDEX idx_paper_reference_paper_id ON paper_reference(paper_id);
CREATE INDEX idx_paper_reference_referenced_ids ON paper_reference USING gin(referenced_paper_ids);

-- Index for links

-- table for cited by


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
