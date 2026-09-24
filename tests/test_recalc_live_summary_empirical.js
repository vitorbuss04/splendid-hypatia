/**
 * Adversarial Empirical Verification Suite for recalcLiveSummary()
 * Focus: Milestone 3 — Pricing Math, Live Summary & Visual Indicators
 * 
 * Verifies:
 * 1. Zero plates / zero weights / zero times
 * 2. High volume project (10+ plates, 100+ BOM items) with precision oracle & performance benchmark
 * 3. Commercial discount edge cases (0%, 50%, 100%, >100% clamping)
 * 4. Negative net profit (discount exceeds margin, extreme taxes) & text-rose-400 alerts
 * 5. Dynamic margin pill coloring (green >=20%, yellow >=5%, red <0%, neutral 0..4.9%)
 * 6. Cost distribution bar segment width calculation and 0 base cost handling (all 20%)
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// 1. Setup simulated DOM
const elements = {};
function getOrCreate(id) {
    if (!elements[id]) {
        elements[id] = {
            id,
            textContent: '',
            value: '',
            className: '',
            style: {},
            classList: {
                classes: new Set(),
                add(c) { this.classes.add(c); elements[id].className = Array.from(this.classes).join(' '); },
                remove(c) { this.classes.delete(c); elements[id].className = Array.from(this.classes).join(' '); },
                contains(c) { return this.classes.has(c); }
            }
        };
    }
    return elements[id];
}

const querySelectorRegistry = {};
function registerSelector(sel, el) {
    querySelectorRegistry[sel] = el;
}

// Visual indicator elements
const marginPill = {
    textContent: '',
    className: 'profit-margin-pill',
    style: {}
};
registerSelector('.profit-margin-pill', marginPill);

const barMat = { style: {} };
const barMach = { style: {} };
const barLabor = { style: {} };
const barBom = { style: {} };
const barOver = { style: {} };

registerSelector('.cost-bar-mat', barMat);
registerSelector('.cost-bar-mach', barMach);
registerSelector('.cost-bar-labor', barLabor);
registerSelector('.cost-bar-bom', barBom);
registerSelector('.cost-bar-over', barOver);

const sandbox = {
    document: {
        getElementById(id) {
            return getOrCreate(id);
        },
        querySelector(sel) {
            return querySelectorRegistry[sel] || null;
        },
        querySelectorAll(sel) {
            return [];
        },
        addEventListener() {},
        removeEventListener() {}
    },
    addEventListener() {},
    removeEventListener() {},
    console,
    Math,
    Number,
    String,
    parseInt,
    parseFloat,
    isNaN,
    Intl,
    Event: class Event {},
    showToast() {},
    refreshIcons() {}
};
sandbox.window = sandbox;
sandbox.global = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

// 2. Load actual frontend/js/app.js into sandbox
const appJsPath = path.resolve(__dirname, '../frontend/js/app.js');
let appJsCode = fs.readFileSync(appJsPath, 'utf8');
appJsCode += '\nglobalThis.__app_state = state;\nglobalThis.__recalcLiveSummary = recalcLiveSummary;\nglobalThis.__formatCurrency = formatCurrency;\nglobalThis.__parseLocaleFloat = parseLocaleFloat;';

vm.runInContext(appJsCode, sandbox);

const state = sandbox.__app_state;
const recalcLiveSummary = sandbox.__recalcLiveSummary;
const formatCurrency = sandbox.__formatCurrency;
const parseLocaleFloat = sandbox.__parseLocaleFloat;

console.log('✅ app.js successfully evaluated into execution environment');

// Configure printers and filaments in app state
state.printers = [
    { id: 1, name: 'Bambu Lab X1-Carbon', machine_hourly_rate: 6.50 },
    { id: 2, name: 'Prusa MK4', machine_hourly_rate: 3.50 }
];
state.filaments = [
    { id: 1, name: 'PLA Matte Charcoal', spool_weight_g: 1000, spool_price: 110.0, cost_per_gram: 0.11 },
    { id: 2, name: 'PETG Prusament Galaxy', spool_weight_g: 1000, spool_price: 140.0, cost_per_gram: 0.14 }
];

function resetInputs() {
    getOrCreate('proj-cad-hours').value = '0';
    getOrCreate('proj-cad-rate').value = '50';
    getOrCreate('proj-post-hours').value = '0';
    getOrCreate('proj-post-rate').value = '30';
    getOrCreate('proj-overhead').value = '0';
    getOrCreate('proj-margin').value = '30';
    getOrCreate('proj-tax').value = '0';
    getOrCreate('proj-discount').value = '0';
    getOrCreate('proj-shipping').value = '0';
    state.currentPlates = [];
    state.currentBOM = [];
}

let totalTests = 0;
let passedTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        resetInputs();
        fn();
        console.log(`  ✓ PASS: ${name}`);
        passedTests++;
    } catch (err) {
        console.error(`  ✗ FAIL: ${name}`);
        console.error(err);
        process.exitCode = 1;
    }
}

console.log('\n--- SUITE 1: Zero Plates / Zero Weights / Zero Times ---');

runTest('1.1 Completely empty project (0 plates, 0 BOM, 0 labor, 0 overhead)', () => {
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-base-cost').textContent, formatCurrency(0), 'Base cost should be 0');
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(0), 'Suggested price should be 0');
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(0), 'Final price should be 0');
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(0)} (0.0%)`, 'Net profit should be 0');
    assert.strictEqual(getOrCreate('live-weight').textContent, '0.0 g');
    assert.strictEqual(getOrCreate('live-time').textContent, '0.0 h');
    assert.strictEqual(marginPill.textContent, '+0.0%');
    assert.ok(marginPill.className.includes('bg-slate-800'), 'Margin pill should use neutral slate style on 0 base cost');
    assert.strictEqual(barMat.style.width, '20%');
    assert.strictEqual(barMach.style.width, '20%');
    assert.strictEqual(barLabor.style.width, '20%');
    assert.strictEqual(barBom.style.width, '20%');
    assert.strictEqual(barOver.style.width, '20%');
});

runTest('1.2 Single plate with 0 weights and 0 times', () => {
    state.currentPlates = [{
        name: 'Placa Zero',
        printer_id: 1,
        filament_id: 1,
        print_time_hours: 0,
        part_weight_g: 0,
        purge_weight_g: 0,
        failure_margin_percent: 10,
        quantity: 1
    }];
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-material-cost').textContent, formatCurrency(0));
    assert.strictEqual(getOrCreate('live-machine-cost').textContent, formatCurrency(0));
    assert.strictEqual(getOrCreate('live-base-cost').textContent, formatCurrency(0));
    assert.strictEqual(getOrCreate('plate-cost-0').textContent, formatCurrency(0));
    assert.ok(getOrCreate('plate-summary-text-0').textContent.includes('1x • 0.0h • 0.0g'));
});

runTest('1.3 Zero base cost with non-zero shipping cost', () => {
    getOrCreate('proj-shipping').value = '35.50';
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-base-cost').textContent, formatCurrency(0));
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(35.50));
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(0)} (0.0%)`);
    assert.strictEqual(barMat.style.width, '20%');
});

console.log('\n--- SUITE 2: High Volume Project (10+ Plates, 100+ BOM items) ---');

runTest('2.1 15 plates + 120 BOM items precision oracle & performance benchmark', () => {
    let oraclePlatesCost = 0;
    let oracleMaterialCost = 0;
    let oracleMachineCost = 0;
    let oracleTimeHours = 0;
    let oracleWeightGrams = 0;

    for (let i = 0; i < 15; i++) {
        const qty = (i % 4) + 1; // 1 to 4
        const time = Number(((i + 1) * 0.75).toFixed(2));
        const partW = (i + 1) * 20.0;
        const purgeW = (i % 2 === 0) ? 5.0 : 0.0;
        const failRate = (i % 3) * 5; // 0%, 5%, 10%
        const failFactor = 1.0 + (failRate / 100);
        const printerId = (i % 2 === 0) ? 1 : 2; // rate 6.50 or 3.50
        const machineRate = printerId === 1 ? 6.50 : 3.50;
        const filId = (i % 2 === 0) ? 1 : 2; // cpg 0.11 or 0.14
        const cpg = filId === 1 ? 0.11 : 0.14;

        const effectiveW = (partW + purgeW) * failFactor;
        const uMat = effectiveW * cpg;
        const uMach = time * machineRate;
        const uTotal = uMat + uMach;
        const pTotal = uTotal * qty;

        oraclePlatesCost += pTotal;
        oracleMaterialCost += uMat * qty;
        oracleMachineCost += uMach * qty;
        oracleTimeHours += time * qty;
        oracleWeightGrams += (partW + purgeW) * qty;

        state.currentPlates.push({
            name: `Placa ${i + 1}`,
            printer_id: printerId,
            filament_id: filId,
            print_time_hours: time,
            part_weight_g: partW,
            purge_weight_g: purgeW,
            failure_margin_percent: failRate,
            quantity: qty
        });
    }

    // Generate 120 diverse BOM items
    let oracleBOMCost = 0;
    for (let j = 0; j < 120; j++) {
        const qty = (j % 10) + 1;
        const unit = Number(((j + 1) * 0.35).toFixed(2));
        const sub = qty * unit;
        oracleBOMCost += sub;

        state.currentBOM.push({
            name: `BOM Insumo ${j + 1}`,
            quantity: qty,
            unit_cost: unit
        });
    }

    // Labor and overhead
    getOrCreate('proj-cad-hours').value = '5';
    getOrCreate('proj-cad-rate').value = '80'; // 400
    getOrCreate('proj-post-hours').value = '4';
    getOrCreate('proj-post-rate').value = '40'; // 160
    const oracleLabor = 400 + 160; // 560
    getOrCreate('proj-overhead').value = '120'; // 120
    const oracleOverhead = 120;

    const oracleBaseCost = oraclePlatesCost + oracleBOMCost + oracleLabor + oracleOverhead;

    getOrCreate('proj-margin').value = '35'; // 35%
    getOrCreate('proj-tax').value = '6'; // 6%
    getOrCreate('proj-discount').value = '5'; // 5%
    getOrCreate('proj-shipping').value = '45'; // 45

    const taxDivisor = 1.0 - (6 / 100);
    const oracleSuggested = (oracleBaseCost * (1.0 + 0.35)) / taxDivisor;
    const oracleDiscountAmount = oracleSuggested * 0.05;
    const oracleSubtotalAfterDisc = oracleSuggested - oracleDiscountAmount;
    const oracleTaxAmount = oracleSubtotalAfterDisc * 0.06;
    const oracleNetRev = oracleSubtotalAfterDisc - oracleTaxAmount;
    const oracleNetProfit = oracleNetRev - oracleBaseCost;
    const oracleFinalPrice = oracleSubtotalAfterDisc + 45;
    const oracleEffMargin = (oracleNetProfit / oracleBaseCost) * 100;

    // Benchmark execution time
    const t0 = process.hrtime.bigint();
    recalcLiveSummary();
    const t1 = process.hrtime.bigint();
    const durationMs = Number(t1 - t0) / 1e6;

    console.log(`     -> Recalculation time for 15 plates + 120 BOM items: ${durationMs.toFixed(3)} ms`);
    assert.ok(durationMs < 50, `Calculation should take < 50ms, took ${durationMs}ms`);

    // Verify weights and times
    assert.strictEqual(getOrCreate('live-weight').textContent, `${oracleWeightGrams.toFixed(1)} g`);
    assert.strictEqual(getOrCreate('live-time').textContent, `${oracleTimeHours.toFixed(1)} h`);

    // Verify costs
    assert.strictEqual(getOrCreate('live-material-cost').textContent, formatCurrency(oracleMaterialCost));
    assert.strictEqual(getOrCreate('live-machine-cost').textContent, formatCurrency(oracleMachineCost));
    assert.strictEqual(getOrCreate('live-bom-cost').textContent, formatCurrency(oracleBOMCost));
    assert.strictEqual(getOrCreate('live-labor-cost').textContent, formatCurrency(oracleLabor));
    assert.strictEqual(getOrCreate('live-overhead-cost').textContent, formatCurrency(oracleOverhead));
    assert.strictEqual(getOrCreate('live-base-cost').textContent, formatCurrency(oracleBaseCost));
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(oracleFinalPrice));
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(oracleSuggested));

    // Verify cost distribution bar percentages add up to ~100%
    const pMat = parseFloat(barMat.style.width);
    const pMach = parseFloat(barMach.style.width);
    const pLabor = parseFloat(barLabor.style.width);
    const pBom = parseFloat(barBom.style.width);
    const pOver = parseFloat(barOver.style.width);
    const totalBarP = pMat + pMach + pLabor + pBom + pOver;
    assert.ok(Math.abs(totalBarP - 100) < 0.5, `Bar percentages sum should be ~100%, got ${totalBarP}%`);
});

console.log('\n--- SUITE 3: Commercial Discount Edge Cases ---');

runTest('3.1 Discount = 0%', () => {
    getOrCreate('proj-overhead').value = '100'; // baseCost = 100
    getOrCreate('proj-margin').value = '20'; // margin = 20% -> price = 120
    getOrCreate('proj-tax').value = '0';
    getOrCreate('proj-discount').value = '0';
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(120));
    assert.strictEqual(getOrCreate('live-discount-amount').textContent, `- ${formatCurrency(0)}`);
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(120));
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(20)} (20.0%)`);
    assert.ok(marginPill.className.includes('bg-emerald-500/15'), '20% should be emerald');
});

runTest('3.2 Discount = 50%', () => {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = '20'; // suggested = 120
    getOrCreate('proj-discount').value = '50'; // disc = 60 -> final = 60
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(120));
    assert.strictEqual(getOrCreate('live-discount-amount').textContent, `- ${formatCurrency(60)}`);
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(60));
    // Net profit = 60 - 100 = -40 (-40.0%)
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(-40)} (-40.0%)`);
    assert.ok(marginPill.className.includes('bg-rose-500/15'), 'Negative profit should be rose alert');
    assert.strictEqual(marginPill.textContent, '-40.0%');
});

runTest('3.3 Discount = 100%', () => {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = '20'; // suggested = 120
    getOrCreate('proj-discount').value = '100'; // disc = 120 -> final = 0
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(120));
    assert.strictEqual(getOrCreate('live-discount-amount').textContent, `- ${formatCurrency(120)}`);
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(0));
    // Net profit = 0 - 100 = -100 (-100.0%)
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(-100)} (-100.0%)`);
    assert.ok(marginPill.className.includes('bg-rose-500/15'));
    assert.strictEqual(marginPill.textContent, '-100.0%');
});

runTest('3.4 Discount clamping: >100% discount should clamp to 100%', () => {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = '20';
    getOrCreate('proj-discount').value = '150'; // Should clamp to 100%
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-discount-amount').textContent, `- ${formatCurrency(120)}`);
    assert.strictEqual(getOrCreate('live-final-price').textContent, formatCurrency(0));
    assert.strictEqual(marginPill.textContent, '-100.0%');
});

console.log('\n--- SUITE 4: Negative Net Profit & Extreme Tax Edge Cases ---');

runTest('4.1 Discount slightly exceeds margin -> negative net profit alert', () => {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = '10'; // suggested = 110
    getOrCreate('proj-discount').value = '15'; // 15% disc = 16.50 -> final = 93.50
    recalcLiveSummary();
    // Net profit = 93.50 - 100 = -6.50 (-6.5%)
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(-6.50)} (-6.5%)`);
    assert.ok(getOrCreate('live-net-profit').className.includes('text-rose-400'));
    assert.ok(marginPill.className.includes('bg-rose-500/15 text-rose-400'));
    assert.strictEqual(marginPill.textContent, '-6.5%');
});

runTest('4.2 High tax rate edge case: 90% tax rate', () => {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = '10';
    getOrCreate('proj-tax').value = '90';
    // taxDivisor = 1 - 0.90 = 0.10 -> suggested = (100 * 1.1) / 0.1 = 1100
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(1100));
    assert.strictEqual(getOrCreate('live-tax-amount').textContent, formatCurrency(990));
    // netRevenue = 1100 - 990 = 110. netProfit = 110 - 100 = 10 (10.0%)
    assert.strictEqual(getOrCreate('live-net-profit').textContent, `${formatCurrency(10)} (10.0%)`);
    assert.ok(marginPill.className.includes('bg-amber-500/15'), '10% should be amber');
});

runTest('4.3 Boundary tax rate: 99% tax rate does not divide by zero or NaN', () => {
    getOrCreate('proj-overhead').value = '10';
    getOrCreate('proj-margin').value = '0';
    getOrCreate('proj-tax').value = '99';
    // taxDivisor = 1 - 0.99 = 0.01 -> suggested = 10 / 0.01 = 1000
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(1000));
    assert.ok(!getOrCreate('live-final-price').textContent.includes('NaN'));
    assert.ok(!getOrCreate('live-final-price').textContent.includes('Infinity'));
});

runTest('4.4 Tax clamping: tax > 99% clamps to 99% avoiding divisor <= 0', () => {
    getOrCreate('proj-overhead').value = '10';
    getOrCreate('proj-margin').value = '0';
    getOrCreate('proj-tax').value = '105'; // Should clamp to 99%
    recalcLiveSummary();
    assert.strictEqual(getOrCreate('live-suggested-price').textContent, formatCurrency(1000));
    assert.ok(!getOrCreate('live-final-price').textContent.includes('NaN'));
    assert.ok(!getOrCreate('live-final-price').textContent.includes('Infinity'));
});

console.log('\n--- SUITE 5: Dynamic Margin Pill Coloring Tiers ---');

function testMarginTier(margin, discount, expectedColorClass, expectedSign) {
    getOrCreate('proj-overhead').value = '100';
    getOrCreate('proj-margin').value = String(margin);
    getOrCreate('proj-discount').value = String(discount);
    getOrCreate('proj-tax').value = '0';
    recalcLiveSummary();
    assert.ok(
        marginPill.className.includes(expectedColorClass),
        `Margin pill with margin=${margin}, disc=${discount} expected ${expectedColorClass}, got ${marginPill.className}`
    );
    if (expectedSign) {
        assert.ok(marginPill.textContent.startsWith(expectedSign), `Expected sign '${expectedSign}' in '${marginPill.textContent}'`);
    }
}

runTest('5.1 Green (Emerald) tier >= 20.0%', () => {
    testMarginTier(30, 0, 'bg-emerald-500/15', '+'); // 30% -> emerald
    testMarginTier(20, 0, 'bg-emerald-500/15', '+'); // exactly 20.0% -> emerald
    testMarginTier(20.1, 0, 'bg-emerald-500/15', '+'); // 20.1% -> emerald
});

runTest('5.2 Yellow/Amber tier >= 5.0% and < 20.0%', () => {
    testMarginTier(19.9, 0, 'bg-amber-500/15', '+'); // 19.9% -> amber
    testMarginTier(10.0, 0, 'bg-amber-500/15', '+'); // 10.0% -> amber
    testMarginTier(5.0, 0, 'bg-amber-500/15', '+'); // exactly 5.0% -> amber
});

runTest('5.3 Neutral Slate tier >= 0.0% and < 5.0%', () => {
    testMarginTier(4.9, 0, 'bg-slate-800', '+'); // 4.9% -> slate
    testMarginTier(1.0, 0, 'bg-slate-800', '+'); // 1.0% -> slate
    testMarginTier(0.0, 0, 'bg-slate-800', '+'); // 0.0% -> slate
});

runTest('5.4 Red/Rose Alert tier < 0.0%', () => {
    testMarginTier(10, 15, 'bg-rose-500/15', '-'); // -6.5% -> rose
    testMarginTier(0, 10, 'bg-rose-500/15', '-'); // -10.0% -> rose
    testMarginTier(20, 50, 'bg-rose-500/15', '-'); // -40.0% -> rose
});

console.log('\n--- SUITE 6: Cost Distribution Bar Segment Widths ---');

runTest('6.1 Base cost 0 -> all 5 segments default to 20%', () => {
    getOrCreate('proj-overhead').value = '0';
    recalcLiveSummary();
    assert.strictEqual(barMat.style.width, '20%');
    assert.strictEqual(barMach.style.width, '20%');
    assert.strictEqual(barLabor.style.width, '20%');
    assert.strictEqual(barBom.style.width, '20%');
    assert.strictEqual(barOver.style.width, '20%');
});

runTest('6.2 Equal distribution: each category has exactly 20.00 base cost', () => {
    // Material = 20, Machine = 20
    state.currentPlates = [{
        name: 'Equal Plate',
        printer_id: null,
        filament_id: null,
        custom_printer_hourly_rate: 20.0,
        custom_filament_cost_per_g: 1.0,
        print_time_hours: 1.0, // 20.0 machine
        part_weight_g: 20.0,   // 20.0 material
        purge_weight_g: 0,
        failure_margin_percent: 0,
        quantity: 1
    }];
    // BOM = 20
    state.currentBOM = [{ quantity: 1, unit_cost: 20.0 }];
    // Labor = 20 (CAD: 20, Post: 0)
    getOrCreate('proj-cad-hours').value = '1';
    getOrCreate('proj-cad-rate').value = '20';
    // Overhead = 20
    getOrCreate('proj-overhead').value = '20';

    // Total base = 100. Each category is exactly 20%
    recalcLiveSummary();
    assert.strictEqual(barMat.style.width, '20.0%');
    assert.strictEqual(barMach.style.width, '20.0%');
    assert.strictEqual(barLabor.style.width, '20.0%');
    assert.strictEqual(barBom.style.width, '20.0%');
    assert.strictEqual(barOver.style.width, '20.0%');
});

runTest('6.3 Skewed distribution: 100% material, 0% all others', () => {
    state.currentPlates = [{
        name: 'Mat Only',
        printer_id: null,
        filament_id: null,
        custom_printer_hourly_rate: 0,
        custom_filament_cost_per_g: 1.0,
        print_time_hours: 0,
        part_weight_g: 100.0,
        purge_weight_g: 0,
        failure_margin_percent: 0,
        quantity: 1
    }];
    recalcLiveSummary();
    assert.strictEqual(barMat.style.width, '100.0%');
    assert.strictEqual(barMach.style.width, '0.0%');
    assert.strictEqual(barLabor.style.width, '0.0%');
    assert.strictEqual(barBom.style.width, '0.0%');
    assert.strictEqual(barOver.style.width, '0.0%');
});

console.log(`\n========================================`);
console.log(`RESULTS: ${passedTests}/${totalTests} tests passed`);
console.log(`========================================\n`);

if (passedTests !== totalTests) {
    process.exit(1);
} else {
    process.exit(0);
}
