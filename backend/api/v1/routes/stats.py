"""
Statistics-related API routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import re

from ..models.stats import StatsResponse, TrendResponse, TrendData, YearTrend
from ..models.base import ErrorResponse

stats_router = APIRouter(prefix="/stats", tags=["statistics"])


@stats_router.get("/trends/yearly", response_model=TrendResponse)
async def get_yearly_publication_trends(
    start_year: Optional[int] = Query(None, ge=1950, le=2030, description="Start year filter"),
    end_year: Optional[int] = Query(None, ge=1950, le=2030, description="End year filter"),
    cluster: Optional[str] = Query(None, description="Filter by cluster"),
    topic: Optional[str] = Query(None, description="Filter by topic")
):
    """
    Get yearly publication trends showing number of papers published each year
    
    Supports filtering by year range, cluster, and topic
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Build the base query with year extraction from various possible date formats
            base_query = """
                WITH extracted_years AS (
                    SELECT 
                        paper_id,
                        title,
                        cluster,
                        topic,
                        -- Try to extract year from various sources in json_data
                        COALESCE(
                            -- Try published_date field (format: "2014 Aug 18")
                            CASE 
                                WHEN json_data->>'published_date' ~ '^[0-9]{4}' 
                                THEN substring(json_data->>'published_date' from '^([0-9]{4})')::int
                            END,
                            -- Try year field if it exists
                            CASE 
                                WHEN json_data->>'year' ~ '^[0-9]{4}$' 
                                THEN (json_data->>'year')::int
                            END,
                            -- Try publication_date field
                            CASE 
                                WHEN json_data->>'publication_date' ~ '[0-9]{4}' 
                                THEN substring(json_data->>'publication_date' from '[0-9]{4}')::int
                            END,
                            -- Try date field
                            CASE 
                                WHEN json_data->>'date' ~ '[0-9]{4}' 
                                THEN substring(json_data->>'date' from '[0-9]{4}')::int
                            END
                        ) as publication_year
                    FROM paper 
                    WHERE title IS NOT NULL AND json_data IS NOT NULL
                ),
                filtered_papers AS (
                    SELECT * FROM extracted_years
                    WHERE publication_year IS NOT NULL
                        AND publication_year BETWEEN 1950 AND 2030  -- Reasonable year range
            """
            
            # Add filters
            filters = []
            params = []
            param_count = 1
            
            if start_year:
                filters.append(f"AND publication_year >= ${param_count}")
                params.append(start_year)
                param_count += 1
                
            if end_year:
                filters.append(f"AND publication_year <= ${param_count}")
                params.append(end_year)
                param_count += 1
                
            if cluster:
                filters.append(f"AND cluster = ${param_count}")
                params.append(cluster)
                param_count += 1
                
            if topic:
                filters.append(f"AND topic ILIKE ${param_count}")
                params.append(f"%{topic}%")
                param_count += 1
            
            # Complete the query
            query = base_query + "\n".join(filters) + """
                )
                SELECT 
                    publication_year,
                    COUNT(*) as paper_count
                FROM filtered_papers
                GROUP BY publication_year
                ORDER BY publication_year ASC
            """
            
            yearly_data = await conn.fetch(query, *params)
        
            if not yearly_data:
                return TrendResponse(
                    success=True,
                    data=TrendData(
                        yearly_trends=[],
                        total_papers=0,
                        year_range={"min_year": 0, "max_year": 0},
                        peak_year={"year": 0, "count": 0}
                    ),
                    message="No publication data found for the specified filters"
                )
            
            # Process the data
            yearly_trends = [
                YearTrend(year=row['publication_year'], count=row['paper_count']) 
                for row in yearly_data
            ]
            
            total_papers = sum(trend.count for trend in yearly_trends)
            min_year = min(trend.year for trend in yearly_trends)
            max_year = max(trend.year for trend in yearly_trends)
            peak_year_data = max(yearly_trends, key=lambda x: x.count)
            
            # Get summary statistics
            summary_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_in_db,
                    COUNT(CASE WHEN json_data IS NOT NULL THEN 1 END) as with_json,
                    COUNT(CASE WHEN cluster IS NOT NULL THEN 1 END) as with_cluster,
                    COUNT(CASE WHEN topic IS NOT NULL THEN 1 END) as with_topic
                FROM paper
            """)
            
            trend_data = TrendData(
                yearly_trends=yearly_trends,
                total_papers=total_papers,
                year_range={
                    "min_year": min_year,
                    "max_year": max_year,
                    "span_years": max_year - min_year + 1
                },
                peak_year={
                    "year": peak_year_data.year,
                    "count": peak_year_data.count,
                    "percentage": round((peak_year_data.count / total_papers) * 100, 2)
                }
            )
            
            message = f"Retrieved publication trends for {len(yearly_trends)} years ({min_year}-{max_year}) with {total_papers} papers"
            if cluster:
                message += f" in cluster '{cluster}'"
            if topic:
                message += f" with topic containing '{topic}'"
                
            return TrendResponse(
                success=True,
                data=trend_data,
                message=message
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve publication trends: {str(e)}")


@stats_router.get("/trends/monthly")
async def get_monthly_publication_trends(
    year: int = Query(..., ge=1950, le=2030, description="Year to analyze monthly trends"),
    cluster: Optional[str] = Query(None, description="Filter by cluster")
):
    """
    Get monthly publication trends for a specific year
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Query for monthly data within a specific year
            query = """
                WITH monthly_data AS (
                    SELECT 
                        EXTRACT(MONTH FROM created_at) as month,
                        COUNT(*) as paper_count
                    FROM paper 
                    WHERE EXTRACT(YEAR FROM created_at) = $1
                        AND title IS NOT NULL
            """
            
            params = [year]
            
            if cluster:
                query += " AND cluster = $2"
                params.append(cluster)
                
            query += """
                    GROUP BY EXTRACT(MONTH FROM created_at)
                    ORDER BY month
                )
                SELECT 
                    month,
                    paper_count,
                    -- Month names for better display
                    CASE month
                        WHEN 1 THEN 'January'
                        WHEN 2 THEN 'February' 
                        WHEN 3 THEN 'March'
                        WHEN 4 THEN 'April'
                        WHEN 5 THEN 'May'
                        WHEN 6 THEN 'June'
                        WHEN 7 THEN 'July'
                        WHEN 8 THEN 'August'
                        WHEN 9 THEN 'September'
                        WHEN 10 THEN 'October'
                        WHEN 11 THEN 'November'
                        WHEN 12 THEN 'December'
                    END as month_name
                FROM monthly_data
            """
            
            monthly_data = await conn.fetch(query, *params)
            
            monthly_trends = [
                {
                    "month": int(row['month']),
                    "month_name": row['month_name'],
                    "count": row['paper_count']
                }
                for row in monthly_data
            ]
            
            total_year_papers = sum(item["count"] for item in monthly_trends)
            
            return {
                "success": True,
                "data": {
                    "year": year,
                    "monthly_trends": monthly_trends,
                    "total_papers": total_year_papers,
                    "months_with_data": len(monthly_trends)
                },
                "message": f"Retrieved monthly publication data for {year} with {total_year_papers} papers across {len(monthly_trends)} months"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monthly trends: {str(e)}")


# Note: Most statistics are handled in the papers router (/papers/stats)
# This router can be extended for additional statistical endpoints if needed
