-- COMP3311 23T3 Assignment 1
--
-- Fill in the gaps ("...") below with your code
-- You can add any auxiliary views/function that you like
-- but they must be defined in this file *before* their first use
-- The code in this file *MUST* load into an empty database in one pass
-- It will be tested as follows:
-- createdb test; psql test -f ass1.dump; psql test -f ass1.sql
-- Make sure it can load without error under these conditions

-- Put any views/functions that might be useful in multiple questions here



---- Q1
CREATE OR REPLACE VIEW Q1 AS
SELECT 
    region AS state,
    COUNT(b.*) AS nbreweries
FROM locations l
    INNER JOIN breweries b ON l.id = b.located_in
WHERE country = 'Australia'
GROUP BY region;


---- Q2
CREATE OR REPLACE VIEW Q2 AS
SELECT
    name AS style,
    min_abv,
    max_abv
FROM styles
WHERE max_abv - min_abv = (
    SELECT MAX(max_abv - min_abv)
    FROM styles
);


---- Q3
CREATE OR REPLACE VIEW Q3 AS
SELECT
    s.name AS style,
    MIN(b.abv) AS lo_abv,
    MAX(b.abv) AS hi_abv,
    s.min_abv,
    s.max_abv
FROM styles s
INNER JOIN beers b ON s.id = b.style
GROUP BY s.name, s.min_abv, s.max_abv
HAVING s.min_abv != s.max_abv AND (
    MIN(b.abv) < s.min_abv OR MAX(b.abv) > s.max_abv
);


---- Q4
CREATE OR REPLACE VIEW Q4 AS
WITH brewery_ratings AS (
    SELECT 
        br.name AS brewery,
        AVG(be.rating) AS rating
    FROM brewed_by bb
    INNER JOIN breweries br ON bb.brewery = br.id
    INNER JOIN beers be ON bb.beer = be.id
    WHERE be.rating IS NOT NULL
    GROUP BY br.name
    HAVING COUNT(be.rating) >= 5
)
SELECT
    brewery,
    CAST(rating AS NUMERIC(3,1)) AS rating
FROM brewery_ratings
WHERE rating = (SELECT MAX(rating) FROM brewery_ratings);


---- Q5
CREATE OR REPLACE FUNCTION Q5(pattern TEXT) RETURNS TABLE(beer TEXT, container TEXT, std_drinks NUMERIC) AS $$
    SELECT
        name AS beer,
        volume || 'ml ' || CAST(sold_in AS TEXT) AS container,
        CAST(volume * abv * 0.0008 AS NUMERIC(3,1)) AS std_drinks
    FROM beers 
    WHERE name ILIKE '%' || pattern || '%';
$$ LANGUAGE SQL;


---- Q6
CREATE OR REPLACE FUNCTION Q6(pattern TEXT) RETURNS TABLE(country TEXT, first INTEGER, nbeers INTEGER, rating NUMERIC) AS $$
    SELECT
        country,
        MIN(b.brewed) AS first,
        COUNT(b.*) AS nbeers,
        CAST(AVG(rating) AS NUMERIC(3,1)) AS rating
    FROM breweries br
    LEFT JOIN brewed_by bb ON br.id = bb.brewery
    LEFT JOIN beers b ON bb.beer = b.id
    LEFT JOIN locations l ON br.located_in = l.id
    WHERE l.country ILIKE '%' || pattern || '%'
    GROUP BY country;
$$ LANGUAGE SQL;


---- Q7
CREATE OR REPLACE FUNCTION Q7(_beerID integer) RETURNS TEXT AS $$
DECLARE
    beer_name TEXT;
    ingredients_list TEXT;
BEGIN
    SELECT name INTO beer_name
    FROM beers
    WHERE id = _beerID;

    IF beer_name IS NULL THEN
        RETURN 'No such beer (' || _beerID || ')';
    ELSE
        SELECT COALESCE(
            E'  contains:\n' || STRING_AGG('    ' || ingredients.name || ' (' || ingredients.itype || ')', E'\n' ORDER BY ingredients.name),
            '  no ingredients recorded'
        )
        INTO ingredients_list
        FROM contains
        INNER JOIN ingredients ON contains.ingredient = ingredients.id
        WHERE contains.beer = _beerID;
    
        RETURN '"' || beer_name || E'"\n' || ingredients_list;
    END IF;
END;
$$ LANGUAGE PLPGSQL;


---- Q8
DROP TYPE IF EXISTS BeerHops CASCADE;
CREATE TYPE BeerHops AS (beer TEXT, brewery TEXT, hops TEXT);
CREATE OR REPLACE FUNCTION Q8(pattern TEXT) RETURNS SETOF BeerHops AS $$
DECLARE
    beer_record BeerHops;
BEGIN
    FOR beer_record IN (
        SELECT
            b.name AS beer,
            (
                SELECT STRING_AGG(br.name, '+' ORDER BY br.name)
                FROM beers b2
                LEFT JOIN brewed_by bb ON b2.id = bb.beer
                LEFT JOIN breweries br ON bb.brewery = br.id
                WHERE b2.id = b.id
            ) AS brewery,
            COALESCE(
                STRING_AGG(i.name, ',' ORDER BY i.name),
                'no hops recorded'
            ) AS hops
        FROM beers b
        LEFT JOIN contains c ON b.id = c.beer
        LEFT JOIN ingredients i ON c.ingredient = i.id AND i.itype = 'hop'
        WHERE b.name ILIKE '%' || pattern || '%'
        GROUP BY b.id
    )
    LOOP
        RETURN NEXT beer_record;
    END LOOP;
END;
$$ LANGUAGE PLPGSQL;


---- Q9
DROP TYPE IF EXISTS Collab CASCADE;
CREATE TYPE Collab AS (brewery TEXT, collaborator TEXT);
CREATE OR REPLACE FUNCTION Q9(breweryID INTEGER) RETURNS SETOF Collab AS $$
DECLARE
    collab_record Collab;
    main_brewery TEXT;
BEGIN
    IF NOT EXISTS (SELECT * FROM breweries WHERE id = breweryID) THEN
        RETURN NEXT CAST(('No such brewery (' || breweryID || ')', 'none') AS Collab);
        RETURN;
    ELSE
        SELECT name INTO main_brewery FROM breweries WHERE id = breweryID;
        FOR collab_record IN (
            SELECT DISTINCT
                CASE
                    WHEN row_number() OVER (ORDER BY name) = 1 THEN main_brewery
                    ELSE NULL
                END AS brewery,
                brm.name AS collaborator
            FROM (
                SELECT 
                    br.name AS name
                FROM brewed_by bb
                LEFT JOIN breweries br ON bb.brewery = br.id
                WHERE bb.beer IN (
                    SELECT bb2.beer
                    FROM brewed_by bb2
                    WHERE bb2.brewery = breweryID
                ) AND br.id != breweryID
            ) AS brm
            ORDER BY brm.name
        )
        LOOP
            RETURN NEXT collab_record;
        END LOOP;

        IF NOT FOUND THEN
            RETURN NEXT CAST((main_brewery, 'none') AS Collab);
        END IF;
    END IF;
END;
$$ LANGUAGE PLPGSQL;
