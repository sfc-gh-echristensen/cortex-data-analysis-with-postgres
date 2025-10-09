-- SQL Scripts to Reset Test Transactions to Pending Status
-- Choose the appropriate script based on your needs

-- =============================================================================
-- OPTION 1: Reset specific test transactions (SAFEST)
-- =============================================================================

-- Reset transactions that have "test", "debug", or "cancelled" in their notes
UPDATE transactions 
SET 
    status = 'pending',
    notes = REGEXP_REPLACE(notes, E'\nCANCELLED:.*$', '', 'g')
WHERE 
    status IN ('declined', 'cancelled')
    AND (
        LOWER(notes) LIKE '%test%' 
        OR LOWER(notes) LIKE '%debug%'
        OR LOWER(notes) LIKE '%cancelled:%'
        OR LOWER(merchant) LIKE '%test%'
        OR LOWER(merchant) LIKE '%debug%'
    );

-- =============================================================================
-- OPTION 2: Reset specific merchants (TARGETED)
-- =============================================================================

-- Reset specific test merchants back to pending
UPDATE transactions 
SET 
    status = 'pending',
    notes = REGEXP_REPLACE(notes, E'\nCANCELLED:.*$', '', 'g')
WHERE 
    status IN ('declined', 'cancelled')
    AND merchant IN (
        'Gadget Store',
        'Debug Gadget Store', 
        'Luxury Electronics Store',
        'Unknown Merchant XYZ',
        'Raw SQL Test',
        'Major Airlines'
    );

-- =============================================================================
-- OPTION 3: Reset all declined/cancelled to pending (BROAD)
-- =============================================================================

-- WARNING: This resets ALL declined/cancelled transactions
-- Only use this if you're sure you want to reset everything
UPDATE transactions 
SET 
    status = 'pending',
    notes = REGEXP_REPLACE(notes, E'\nCANCELLED:.*$', '', 'g')
WHERE status IN ('declined', 'cancelled');

-- =============================================================================
-- OPTION 4: Reset recent test transactions (TIME-BASED)
-- =============================================================================

-- Reset transactions from the last 7 days that were declined/cancelled
UPDATE transactions 
SET 
    status = 'pending',
    notes = REGEXP_REPLACE(notes, E'\nCANCELLED:.*$', '', 'g')
WHERE 
    status IN ('declined', 'cancelled')
    AND date >= NOW() - INTERVAL '7 days';

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Check current transaction status distribution
SELECT status, COUNT(*) as count, SUM(amount) as total_amount
FROM transactions 
GROUP BY status 
ORDER BY count DESC;

-- View all pending transactions after reset
SELECT 
    transaction_id,
    merchant,
    amount,
    status,
    date,
    CASE 
        WHEN LENGTH(notes) > 50 THEN LEFT(notes, 50) || '...'
        ELSE notes
    END as notes_preview
FROM transactions 
WHERE status = 'pending'
ORDER BY date DESC;

-- =============================================================================
-- CLEAN UP NOTES (OPTIONAL)
-- =============================================================================

-- Remove all cancellation-related notes from transactions
UPDATE transactions 
SET notes = TRIM(REGEXP_REPLACE(notes, E'CANCELLED:.*?(\n|$)', '', 'g'))
WHERE notes LIKE '%CANCELLED:%';

-- Remove empty or whitespace-only notes
UPDATE transactions 
SET notes = NULL 
WHERE TRIM(COALESCE(notes, '')) = '';
