-- Simple SQL to reset all declined transactions to pending status

-- Reset all declined transactions to pending
UPDATE transactions 
SET status = 'pending'
WHERE status = 'declined';

-- Verification query - check the results
SELECT 
    status, 
    COUNT(*) as count, 
    SUM(amount) as total_amount
FROM transactions 
GROUP BY status 
ORDER BY status;
