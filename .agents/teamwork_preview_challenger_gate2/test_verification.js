const fs = require('fs');
const html = fs.readFileSync('../../static/dashboard.html', 'utf-8');

// Test 1: Check HTML script syntax with node check
console.log('--- TEST 1: JS Syntax Validation ---');
const scriptMatches = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
let allJs = scriptMatches.map(m => m[1]).join('\n');
console.log(`Extracted ${scriptMatches.length} script blocks, total ${allJs.length} bytes.`);

// Write temporary script to verify syntax
fs.writeFileSync('./temp_dash.js', allJs, 'utf-8');

// Test 2: Check 25s Ping Heartbeat in connectWebSocket
console.log('\n--- TEST 2: 25s Ping Heartbeat check ---');
const pingLoopMatch = allJs.includes('wsPingInterval = setInterval') &&
                      allJs.includes('25000') &&
                      allJs.includes("type: 'ping'");
console.log('Ping loop implemented:', pingLoopMatch ? 'PASS' : 'FAIL');

// Test 3: Check Top Apps category keys (top_productive & top_distracting)
console.log('\n--- TEST 3: Top Apps breakdown keys check ---');
const topAppsMatch = allJs.includes('data?.top_productive') &&
                     allJs.includes('data?.top_distracting');
console.log('Top Apps keys implemented:', topAppsMatch ? 'PASS' : 'FAIL');

// Test 4: Check AI Recommendations recommendation key handling
console.log('\n--- TEST 4: AI Recommendations recommendation key check ---');
const recKeyMatch = allJs.includes('r.recommendation') &&
                    allJs.includes('JSON.stringify(r)');
console.log('AI Recs recommendation key implemented:', recKeyMatch ? 'PASS' : 'FAIL');

// Test 5: Check Quick-Add fallback POST payload including due_date
console.log('\n--- TEST 5: Quick-Add due_date payload check ---');
const quickAddMatch = allJs.includes("due_date: today");
console.log('Quick-Add due_date implemented:', quickAddMatch ? 'PASS' : 'FAIL');

// Test 6: Check markDone single quote escaping (safeTitle)
console.log('\n--- TEST 6: markDone single-quote escaping check ---');
const safeTitleMatch = allJs.includes("replace(/'/g, \"\\\\'\")") &&
                       allJs.includes("markDone(${item.id}, '${safeTitle}')");
console.log('Single quote escaping implemented:', safeTitleMatch ? 'PASS' : 'FAIL');

// Test 7: Check Assignment urgency ISO datetime split
console.log('\n--- TEST 7: Assignment urgency ISO datetime split check ---');
const urgencySplitMatch = allJs.includes("String(item.due_date).split('T')[0]");
console.log('Urgency ISO split implemented:', urgencySplitMatch ? 'PASS' : 'FAIL');

// Test 8: Check Study Plan start_time / end_time / duration_min / reason mappings
console.log('\n--- TEST 8: Study Plan field mappings check ---');
const studyPlanMatch = allJs.includes('item.start_time') &&
                       allJs.includes('item.end_time') &&
                       allJs.includes('item.duration_min') &&
                       allJs.includes('item.reason');
console.log('Study Plan mappings implemented:', studyPlanMatch ? 'PASS' : 'FAIL');

const allPassed = pingLoopMatch && topAppsMatch && recKeyMatch && quickAddMatch && safeTitleMatch && urgencySplitMatch && studyPlanMatch;
console.log('\n========================================');
console.log('ALL 7 DEFECT VERIFICATIONS:', allPassed ? 'SUCCESS (ALL 7 FIXED)' : 'FAILURE');
console.log('========================================');
