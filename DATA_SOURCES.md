# Data Source Plan

This dashboard is designed to be connected to official Korean highway rest stop datasets.

## 1. Rest Stop Traffic Priority

Use: 한국도로공사_휴게소 이용객 및 교통량 현황

Recommended fields:

- route name
- rest stop name
- location
- site area
- operation type
- daily users
- 2024 daily vehicle traffic

Use this to sort the first dashboard page by the busiest/highest-traffic rest stops.

## 2. Rest Stop Facility / Phone / Direction

Use: 한국도로공사_노선별, 방향별 휴게소 편의시설 현황

Recommended fields:

- route name
- rest stop name
- direction
- location
- phone number
- operation status
- facility flags

Use this as the main rest stop identity table.

## 3. Food Menu Data

Use: 한국도로공사 휴게소 푸드메뉴현황 조회 서비스

Recommended fields:

- rest stop code / name
- store name
- food name
- price
- representative menu flag
- nutrition information if provided

Use this as `menu_items.csv`.

## 4. Store / Brand Data

Use: 한국도로공사 휴게소 브랜드 매장현황 조회 서비스

Recommended fields:

- rest stop code / name
- brand name
- store name
- opening time
- closing time
- route name

Use this as `stores.csv`.

## 5. Monthly Sales / Popularity Data

Use: 한국도로공사 휴게소 매장별 월별 판매 상위 5 / 상품별 월별 판매 상위 5

Recommended fields:

- year-month
- rest stop code / name
- store code / name
- product name
- rank

Use this to create popularity charts and recommendation badges.
