<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quotex Signal Bot Pro</title>
    <style>
        :root {
            --bg-color: #0b0e14;
            --card-bg: #131823;
            --border-color: #222b3d;
            --accent-green: #00ecb7;
            --accent-red: #ff3366;
            --text-main: #ffffff;
            --text-secondary: #8492a6;
            --gold: #f5a623;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 10px;
            max-width: 480px;
            margin: 0 auto;
            min-height: 100vh;
        }

        /* Quotex Top Header Bar */
        .top-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .account-info {
            display: flex;
            flex-direction: column;
        }

        .acc-type {
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-weight: bold;
        }

        .acc-balance {
            font-size: 15px;
            font-weight: bold;
            color: var(--gold);
        }

        .deposit-btn {
            background: var(--accent-green);
            color: #000;
            border: none;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 12px;
            border-radius: 4px;
            cursor: pointer;
        }

        /* Action & Reboot Toolbar */
        .toolbar {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 10px;
        }

        .tool-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
        }

        .tool-btn:active {
            background: var(--border-color);
        }

        /* Currency Grid */
        .currency-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5px;
            margin-bottom: 10px;
        }

        .currency-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 4px;
            font-size: 11px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            text-align: center;
        }

        .currency-btn.active {
            background: var(--accent-red);
            color: #fff;
            border-color: var(--accent-red);
            box-shadow: 0 0 10px rgba(255, 51, 102, 0.4);
        }

        /* Time Selection */
        .time-selector {
            display: flex;
            gap: 15px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            align-items: center;
        }

        .time-option {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            cursor: pointer;
        }

        .time-option input {
            accent-color: var(--accent-red);
        }

        /* Main Signal Box */
        .signal-box-wrapper {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }

        .signal-header {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .signal-btn {
            width: 100%;
            padding: 16px;
            font-size: 20px;
            font-weight: 900;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            text-align: center;
            letter-spacing: 1px;
            transition: all 0.2s ease;
        }

        .signal-btn.up {
            background: linear-gradient(135deg, #00b09b, #96c93d);
            background-color: var(--accent-green);
            color: #051310;
            box-shadow: 0 0 15px rgba(0, 236, 183, 0.4);
        }

        /* Status & Confidence Card */
        .status-card {
            display: flex;
            justify-content: space-between;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 10px 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            font-size: 12px;
            font-weight: bold;
        }

        .status-up {
            color: var(--accent-green);
        }

        /* Indicators List */
        .indicators-container {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }

        .indicator-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 9px 12px;
            border-bottom: 1px solid var(--border-color);
            font-size: 12px;
        }

        .indicator-row:last-child {
            border-bottom: none;
        }

        .indicator-name {
            color: var(--text-secondary);
        }

        .indicator-val {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 6px var(--accent-green);
        }
    </style>
</head>
<body>

    <!-- Quotex Header -->
    <div class="top-header">
        <div class="account-info">
            <span class="acc-type">Demo Account</span>
            <span class="acc-balance">$9,871.99</span>
        </div>
        <button class="deposit-btn">Deposit</button>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
        <button class="tool-btn">🔄 Switch Market Feed</button>
        <button class="tool-btn">🔌 Reboot Bot Engine</button>
    </div>

    <!-- Currency Selector Grid -->
    <div class="currency-grid">
        <button class="currency-btn active">EURUSD</button>
        <button class="currency-btn">GBPUSD</button>
        <button class="currency-btn">AUDUSD</button>
        <button class="currency-btn">USDJPY</button>
        <button class="currency-btn">USDCAD</button>
        <button class="currency-btn">NZDUSD</button>
        <button class="currency-btn">EURJPY</button>
        <button class="currency-btn">GBPJPY</button>
    </div>

    <!-- Time Selector -->
    <div class="time-selector">
        <label class="time-option"><input type="radio" name="time" checked> 1m</label>
        <label class="time-option"><input type="radio" name="time"> 2m</label>
        <label class="time-option"><input type="radio" name="time"> 5m</label>
    </div>

    <!-- Main Signal Box -->
    <div class="signal-box-wrapper">
        <div class="signal-header">
            <span>EURUSD (1m)</span>
            <span style="color: var(--accent-green);">1.14692 (+0.01%)</span>
        </div>
        <button class="signal-btn up">UP</button>
    </div>

    <!-- Market State & Confidence -->
    <div class="status-card">
        <div>State: <span class="status-up">UPTREND 📈</span></div>
        <div>Conf: <span style="color: var(--gold);">HIGH 🔥</span></div>
    </div>

    <!-- Technical Indicators Panel -->
    <div class="indicators-container">
        <div class="indicator-row">
            <span class="indicator-name">SMA 20</span>
            <span class="indicator-val">1.14659 <span class="dot"></span></span>
        </div>
        <div class="indicator-row">
            <span class="indicator-name">EMA 12</span>
            <span class="indicator-val">1.14683 <span class="dot"></span></span>
        </div>
        <div class="indicator-row">
            <span class="indicator-name">BB Lower/Upper</span>
            <span class="indicator-val">1.1459 / 1.1473 <span class="dot"></span></span>
        </div>
        <div class="indicator-row">
            <span class="indicator-name">RSI (14)</span>
            <span class="indicator-val">64.7 <span class="dot"></span></span>
        </div>
        <div class="indicator-row">
            <span class="indicator-name">MACD</span>
            <span class="indicator-val">Bullish <span class="dot"></span></span>
        </div>
    </div>

</body>
</html>
