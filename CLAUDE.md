Final update for the AI Telegram bot project.

GOAL
Make the bot production-ready, visually polished, cheaper to run, and better for long-form academic/document workflows. Fix current bugs, add admin tools, add premium document/file modes, improve pricing, and simplify model usage to reduce token cost.

1. MODELS & PROVIDERS
- Add free GitHub Models support.
- Add NIM support.
- Prefer cheaper providers/models by default to reduce token usage and cost.
- For normal text tasks, prioritize lighter models from Groq and OnlySQ first:
  - Llama
  - Gemma
  - Qwen
  - DeepSeek where available
- Keep the router smart: cheap models first, strong models only when needed or on paid tiers.

2. NEW DOCUMENT / FILE MODES
Add support for answering in file form:
- PDF
- DOCX
- Markdown
- TXT

Add separate task modes:
- "Answer in file"
- "Code as file"
- "Coursework mode"
- "Essay / report mode"
- "Academic document mode"

Rules:
- In Plus and above, the bot can read uploaded files and answer with generated files.
- For coding tasks, the default output should be a file if the user requests it.
- For courseworks and reports, allow user to choose output format: PDF, DOCX, or Markdown.

3. COURSEWORK PIPELINE
Add a dedicated coursework mode with a multi-stage pipeline.

MAX tier must get a special 4-stage coursework mode:
Stage 1:
- Use a prompt-planning model.
- Analyze the topic.
- Extract the main themes, subtopics, and search targets.
- Produce a strict prompt for the writing model.
- Reasoning must be in English.
- All instructions to the model must be in English.
- The user request language can be Russian, but internal reasoning can be English.

Stage 2:
- Send themes and search targets to a high-quality search model.
- Search current sources in Russian and English.
- Gather relevant facts, links, and source summaries.
- Build an evidence pack for the final writing model.

Stage 3:
- Send the final prompt plus sources to the strongest generation model.
- The model writes the full coursework text based on sources and task.
- The output must be complete, structured, and academically formatted.

Stage 4:
- A review/checking model verifies:
  - facts
  - logic
  - completeness
  - formatting
  - style
- If everything is fine, it finalizes the document.
- If the user chose a file output, export it as DOCX, PDF, or Markdown.

Important:
- This 4-stage mode is only for MAX tier.
- User gets only one such advanced coursework request per day, even on MAX.
- Extra coursework requests can be bought separately.

4. DAILY LIMITS AND PAID REQUESTS
Implement paid request system:
- Text request: 1 star per 10 text requests
- Photo request: 1 star per 1 image request
- Voice request: 1 star per 1 voice request
- Special coursework request: 10 stars per 1 request

Important:
- The advanced coursework request is limited to 1 per day.
- Users can buy extra requests.
- The bot must clearly show request balance and used quotas.

5. SUBSCRIPTIONS
Set exact prices:
- Plus = 50 stars / month
- Pro = 100 stars / month
- Max = 250 stars / month

Remove any inflated or random prices.
Make the pricing visible in the bot menu and subscription screens.

6. ADMIN PANEL
Add a real admin panel.
The bot currently does not recognize the admin properly; fix that.

Admin features:
- See all users
- See full statistics
- Ban users
- Mute users
- Unban users
- Unmute users
- Change plan manually
- View message/request usage
- View model/provider usage
- Send broadcasts
- Manage promo codes
- Manage subscription bonuses
- View failed requests and provider errors

The admin must be detected correctly by telegram_id.
Add a direct admin entry in the bot menu for the owner.

7. MENU DESIGN
The current menu looks too plain and weak.
Make it feel like a real product, not a raw utility.

Improve:
- buttons
- icons
- stickers or visual accents
- section layout
- subscription cards
- category screens
- admin UI

The bot must feel polished and premium.

8. STARS WITHDRAWAL / REVENUE
Add a clear explanation or admin tooling for how stars are withdrawn from the bot.
If direct withdrawal is not possible through code, add a clear admin note explaining the official Telegram Stars flow and where the revenue is managed.
Do not invent unsupported methods.

9. FILE INPUT / OUTPUT
Add support for reading files in Plus and above:
- PDF
- DOCX
- TXT
- MD
- other text-based study files

If user asks for code, allow the answer to be returned as a file.
If user asks for coursework/report, allow generated document files.

10. BUG FIXES
Fix the current problems:
- requests are not being completed correctly
- prompts are not being expanded properly
- errors in admin handlers
- image generation failures
- provider fallback problems
- expensive provider usage
- missing admin menu

11. ERROR TO FIX
Current error:
TypeError: admin_root() got an unexpected keyword argument 'dispatcher'

Fix all admin handler signatures so they accept the right aiogram arguments.
Audit all handlers for similar signature mismatches.

12. COST REDUCTION
Reduce cost aggressively:
- Use cheaper models first
- Prefer Groq and OnlySQ for simple requests
- Use Llama, Gemma, Qwen for fast/common tasks
- Reserve expensive models for Max or special flows only

13. IMAGE ROUTER
Fix image generation fallback logic.
If a provider fails with 401, 402, 404, 429, the router must:
- log the failure
- mark provider/model temporarily unavailable
- move to the next available provider
- not loop endlessly
- not fail the whole request immediately

14. ADMIN ACCESS AND SECURITY
- Ensure the admin sees all admin menu options.
- Ensure the bot correctly checks the admin telegram_id.
- Protect admin actions with proper authorization.

15. GENERAL QUALITY
- Keep the bot stable.
- Clean the code.
- Remove dead code.
- Remove broken logic.
- Keep everything modular.
- Prioritize reliability and low cost.
- If something is unclear, make the safest production-ready choice.
