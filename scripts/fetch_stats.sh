#!/usr/bin/env bash
# fetch_stats.sh — 抓取 GitHub GraphQL 数据并重建 stats.json 与数据 SVG。
# 依赖：curl、jq、python3(+pillow)。环境变量：GH_TOKEN（PAT）、可选 LOGIN。
# 任何一步失败立即退出（set -e），不会覆写/提交旧数据。
set -euo pipefail

: "${GH_TOKEN:?missing GH_TOKEN}"
LOGIN="${LOGIN:-Sam-dancing-nu1}"
FROM=$(date -u -d '364 days ago' +%Y-%m-%dT00:00:00Z)
TO=$(date -u +%Y-%m-%dT23:59:59Z)
API="https://api.github.com/graphql"

read -r -d '' QUERY <<'GQL' || true
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    login name avatarUrl url
    followers{totalCount} following{totalCount}
    repositories(ownerAffiliations:OWNER,first:100,orderBy:{field:UPDATED_AT,direction:DESC}){
      totalCount
      nodes{name url isFork isArchived stargazerCount
        languages(first:8,orderBy:{field:SIZE,direction:DESC}){
          edges{size node{name color}}}}
    }
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount contributionLevel}}}}
  }
}
GQL

jq -n --arg q "$QUERY" --arg login "$LOGIN" --arg from "$FROM" --arg to "$TO" \
  '{query:$q, variables:{login:$login, from:$from, to:$to}}' > /tmp/payload.json

HTTP_CODE=$(curl -sS -o /tmp/raw.json -w "%{http_code}" \
  --retry 3 --retry-delay 10 --retry-all-errors --max-time 30 \
  -H "Authorization: bearer $GH_TOKEN" \
  -H "Content-Type: application/json" \
  --data @/tmp/payload.json "$API")

if [ "$HTTP_CODE" != "200" ]; then
  echo "FATAL: graphql HTTP $HTTP_CODE" >&2
  exit 1
fi

python3 scripts/transform_stats.py /tmp/raw.json data
python3 scripts/generate_svgs.py
echo "fetch & generate OK"
