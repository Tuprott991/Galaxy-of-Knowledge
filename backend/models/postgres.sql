-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Paper Table
-- ========================================
CREATE TABLE IF NOT EXISTS paper (
    paper_id SERIAL PRIMARY KEY,
    full_text TEXT,
    author_list TEXT[],
    json_data JSONB,
    embeddings vector(768), -- Adjust dimension as needed (e.g., 768 for BERT, 1536 for OpenAI)
    plot_visualize_x FLOAT,
    plot_visualize_y FLOAT,
    plot_visualize_z FLOAT,
    cluster TEXT, 
    -- relatedby: list of paper IDs (string) that write about this paper in their related works
    related_by TEXT[],
    cited_by TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_paper_embeddings ON paper USING ivfflat (embeddings vector_cosine_ops);
CREATE INDEX idx_paper_json ON paper USING gin(json_data);
CREATE INDEX idx_paper_cluster ON paper(cluster);
CREATE INDEX idx_paper_related_by ON paper USING gin(related_by);


-- ========================================
-- Key Knowledge Table
-- ========================================
CREATE TABLE IF NOT EXISTS key_knowledge ( -- Single keyword 
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
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
CREATE TRIGGER update_authors_updated_at BEFORE UPDATE ON authors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_author_updated_at BEFORE UPDATE ON author
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_updated_at BEFORE UPDATE ON paper
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_key_knowledge_updated_at BEFORE UPDATE ON key_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Helpful Views
-- ========================================

-- View: Papers with their authors
CREATE OR REPLACE VIEW paper_with_authors AS
SELECT 
    p.paper_id,
    p.full_text,
    p.json_data,
    p.plot_visualize_x,
    p.plot_visualize_y,
    p.plot_visualize_z,
    json_agg(
        json_build_object(
            'author_id', a.id,
            'author_name', a.name,
            'is_first_author', pa.is_first_author,
            'is_corresponding_author', pa.is_corresponding_author,
            'author_order', pa.author_order
        ) ORDER BY pa.author_order
    ) as authors
FROM paper p
LEFT JOIN paper_authors pa ON p.paper_id = pa.paper_id
LEFT JOIN authors a ON pa.author_id = a.id
GROUP BY p.paper_id;

-- View: Papers with their key knowledge
CREATE OR REPLACE VIEW paper_with_key_knowledge AS
SELECT 
    p.paper_id,
    p.full_text,
    json_agg(
        json_build_object(
            'id', kk.id,
            'context', kk.context
        )
    ) as key_knowledge
FROM paper p
LEFT JOIN key_knowledge kk ON p.paper_id = kk.paper_id
GROUP BY p.paper_id;

-- ========================================
-- Sample queries (commented out)
-- ========================================

-- Find similar papers by embedding
-- SELECT paper_id, embeddings <=> '[0.1, 0.2, ...]'::vector AS distance
-- FROM paper
-- ORDER BY distance
-- LIMIT 10;

-- Get paper with all relations
-- SELECT 
--     p.*,
--     (SELECT json_agg(a.name) FROM paper_authors pa JOIN authors a ON pa.author_id = a.id WHERE pa.paper_id = p.paper_id) as authors,
--     (SELECT json_agg(kk.context) FROM key_knowledge kk WHERE kk.paper_id = p.paper_id) as key_knowledge,
--     (SELECT related FROM paper_pointer WHERE paper_id = p.paper_id) as related_papers,
--     (SELECT refer FROM paper_pointer WHERE paper_id = p.paper_id) as references
-- FROM paper p
-- WHERE p.paper_id = 1;
