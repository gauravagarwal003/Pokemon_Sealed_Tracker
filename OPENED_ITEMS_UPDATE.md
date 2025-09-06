# Market Value Update: Opened Items Excluded

## What Changed

I've updated the system so that **opened items are excluded from your collection's market value**, which reflects the reality that opened Pokemon sealed products have little to no resale value.

## Changes Made:

### 1. Visualization Updates (`visualize_collection.py`)
- **Collection Value Calculation**: Now skips opened items when calculating market value
- **Chart Title**: Updated to "Pokémon Sealed Collection Value Over Time (Sealed Items Only)"
- **Added Note**: Chart now includes disclaimer that only sealed items contribute to value

### 2. Purchase Tracking Updates (`track_purchases.py`)
- **Collection Summary**: Now shows separate counts and costs for sealed vs opened items
- **Clear Messaging**: Indicates "sealed items (market value)" vs "opened items (no market value)"
- **Open Function Warning**: Added clear warning that opening removes market value

### 3. Inventory Display Updates
- **Column Headers**: Now clarify that sealed items "have market value" and opened items have "no market value"
- **Status Tracking**: Better differentiation between sealed, opened, and sold statuses

### 4. User Experience Improvements
- **Clear Warnings**: When opening items, users are warned about market value impact
- **Realistic Tracking**: Collection value now accurately reflects investment potential
- **Educational**: Helps users understand the value impact of opening products

## Example Impact:

### Before:
- 5 ETBs at $45 each = $225 collection value
- Open 2 ETBs
- Still showed $225 collection value ❌

### After:
- 5 ETBs at $45 each = $225 collection value
- Open 2 ETBs → 3 sealed + 2 opened
- New collection value = 3 × $45 = $135 ✅
- **Market value reduced by $90** (realistic impact)

## Benefits:

✅ **Realistic Valuation**: Collection value reflects actual resale potential
✅ **Investment Clarity**: Clear understanding of sealed vs opened value
✅ **Better Decision Making**: Users can see the real cost of opening products
✅ **Accurate ROI**: Return on investment calculations now more precise
✅ **Educational Tool**: Teaches the importance of keeping items sealed for value

## Technical Details:

- Opened items are still tracked for cost basis and quantity
- They can still be sold (at whatever opened price you set)
- Only the market value calculation excludes them
- All purchase history and costs are preserved
- Backward compatible with existing data

This change makes the collection tracker much more realistic and useful for investment tracking!
