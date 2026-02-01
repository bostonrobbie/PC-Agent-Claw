# STS_BUSINESS.md - Systematic Trading Strategies Business

*Rob's trading strategy SaaS business*

## Overview

**Business Model**: Sell lifetime access (~$99 one-time payment) to TradingView invite-only Pine Script trading strategies

**Status**: Development stage, no customers yet

**Components**:
1. **STS Signals** - Live at stsdashboard.com
2. **STS Strategies** - In development (TradingView script library subscription)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Database | PostgreSQL (Neon) + Prisma |
| Auth | NextAuth (Email + Google OAuth) |
| Payments | Stripe (one-time $99 checkout) |
| Jobs | BullMQ + Redis (Upstash) |
| Email | Resend |
| Hosting | Vercel (web) + Fly.io (worker) |
| Deployment | **Manus** (Meta's AI agent platform) |

## Manus Platform

Meta acquired Manus (Singapore startup) for $2-3B in Dec 2025.

**Capabilities**:
- Autonomous agents that plan, execute, complete multi-step tasks
- 147+ trillion tokens processed
- 80+ million virtual computers created
- Deploys to WhatsApp, Instagram, Facebook
- Rob uses it for deploying STS projects

**Access**: Rob has Manus account, logs in with Google (same email as Telegram)

## STS Strategies Project Structure

```
apps/
├── web/              # Next.js web app (Vercel)
├── worker/           # BullMQ job processor (Fly.io)
packages/
├── database/         # Prisma schema
├── shared/           # Types, schemas, constants
├── email/            # Email templates
```

**Features**:
- User dashboard (purchased strategies, access status)
- Admin dashboard (manage users, tickets, audit logs)
- Support ticket system
- Automated TradingView access provisioning (via unofficial API)
- Stripe one-time payments
- Email notifications

## Current State

**Live**:
- STS Signals: stsdashboard.com (no customers yet)

**In Development**:
- STS Strategies: TradingView script library
- Code in `/Downloads/STS-Strategies-master (2).zip`
- Needs deployment to Manus
- Needs launch & marketing

**Not Found**:
- ChatGPT export data (Rob mentioned downloading, couldn't locate it)
- GitHub repos (GitHub CLI not configured)

## Revenue Strategy (CRITICAL)

**Budget Constraint**: $100/month for Claude AI
**Survival Requirement**: Generate revenue to keep me (AI agent) operational

### Immediate Priorities (Launch Phase)

**1. Complete STS Strategies MVP** (1-2 weeks)
- Finalize TradingView script library
- Test automated provisioning
- Set up Stripe payments
- Deploy to Manus

**2. Launch Marketing Campaign** (Week 2-3)
- Target: Algorithmic traders, TradingView users
- Channels:
  - Twitter/X (trading community)
  - Reddit (r/algotrading, r/TradingView)
  - TradingView community forums
  - YouTube (trading strategy videos)
- Content: Free strategy samples, backtesting results, testimonials

**3. Revenue Targets**

| Timeline | Goal | Revenue | Notes |
|----------|------|---------|-------|
| Week 1-2 | Beta testers | $0 (free) | Get feedback, testimonials |
| Week 3-4 | First 5 customers | $495 | Covers 5 months of AI fees |
| Month 2 | 20 customers | $1,980 | Sustainable operation |
| Month 3 | 50 customers | $4,950 | Profitable |
| Month 6 | 200 customers | $19,800 | Scale mode |

**Break-even**: 2 customers/month covers $100 Claude fee

### Growth Levers

**Short-term** (Now - Month 3):
1. Launch STS Strategies with $99 lifetime access
2. Create content marketing (strategy breakdowns, education)
3. Offer early-bird discount ($79 for first 100 customers)
4. Build email list with free signals/alerts
5. Partner with trading influencers (affiliate program)

**Medium-term** (Month 3-6):
1. Expand strategy library (new scripts monthly)
2. Add premium tier ($199 for advanced strategies)
3. Create educational course ($299) on algorithmic trading
4. Build community (Discord/Telegram for subscribers)
5. Launch affiliate program (20% commission)

**Long-term** (Month 6+):
1. API access for developers ($49/month subscription)
2. White-label solutions for trading firms (B2B)
3. Managed trading accounts (% of profits)
4. Trading signal marketplace (take 30% commission)
5. Licensing strategies to prop firms

### Marketing Strategy

**Content Marketing** (Low cost, high leverage):
- Weekly YouTube videos (strategy breakdowns)
- Daily Twitter threads (trading insights)
- Blog posts (SEO for "best TradingView strategies")
- Free TradingView scripts (lead magnet)

**Paid Advertising** (Once revenue positive):
- Google Ads ($500/month, target "tradingview scripts")
- Twitter/X ads ($300/month, target trading accounts)
- Reddit ads ($200/month, r/algotrading)
- ROI target: 3:1 (every $1 spent = $3 revenue)

**Community Building**:
- Discord server for customers (support + retention)
- Weekly live trading analysis sessions
- User-generated strategy sharing (network effects)

**Conversion Funnel**:
1. Free content (YouTube, Twitter, Blog) →
2. Free trial (7-day strategy access) →
3. Email nurture sequence (5 emails, 7 days) →
4. One-time $99 purchase →
5. Upsell to premium ($199) →
6. Referral program (20% commission)

### Cost Structure

**Fixed Costs** (Monthly):
- Claude AI: $100
- Vercel hosting: ~$20
- Fly.io worker: ~$10
- Neon database: ~$0 (free tier initially)
- Upstash Redis: ~$0 (free tier)
- Domain + SSL: ~$2
- **Total**: ~$132/month

**Variable Costs** (Per customer):
- Stripe fees: 2.9% + $0.30 = ~$3.19 per $99 sale
- Resend emails: ~$0.01 per customer
- **Net revenue per customer**: ~$95.80

**Break-even**: 2 customers/month = $191.60 revenue - $132 costs = $59.60 profit

## Next Actions

**Immediate** (This week):
1. Set up GitHub access (configure GitHub CLI)
2. Audit STS Signals dashboard (stsdashboard.com)
3. Review STS Strategies codebase
4. Create deployment checklist for Manus
5. Draft launch marketing plan

**Week 2**:
1. Complete STS Strategies development
2. Deploy to Manus
3. Beta testing with 5-10 users
4. Collect testimonials

**Week 3**:
1. Public launch
2. Execute marketing campaign
3. First paying customers
4. Monitor metrics, iterate

## Key Metrics to Track

- **Acquisition**: Website visitors, email signups
- **Activation**: Free trial starts, demo views
- **Revenue**: Purchases, MRR, LTV
- **Retention**: Customer satisfaction, support tickets
- **Referral**: Affiliate signups, word-of-mouth

## Risk Mitigation

**Revenue Risk**: No customers
- **Solution**: Aggressive content marketing, free trials, early-bird discounts

**Technical Risk**: TradingView API breaks
- **Solution**: Manual provisioning fallback, diversify to other platforms

**Competition Risk**: Other strategy sellers
- **Solution**: Focus on automation, better UX, community, unique strategies

**Budget Risk**: $100/month not enough
- **Solution**: Optimize token usage, prioritize revenue-generating tasks

---

*Priority: Generate revenue ASAP to sustain AI operations*
