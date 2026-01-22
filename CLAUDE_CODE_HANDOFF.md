# Claude Code Handoff: Complex Query Failure Analysis

## პრობლემა

Scoop AI სისტემატურად ვერ ამუშავებს კომპლექსურ შეკითხვებს. ეს არის **სისტემური** პრობლემა, არა ერთი პასუხის bug.

---

## Failing Test Queries

### Query 1: Budget + Prioritization + Dietary
```
მაქვს ლაქტოზის აუტანლობა და ვარ ვეგეტარიანელი. ჯიბეში მაქვს სულ 150 ლარი. 
მჭირდება პროტეინიც, კრეატინიც და ომეგა-3-იც მთელი თვის მარაგისთვის. 
რომელიმე თუ არ მომდის, მითხარი რაზე ვთქვა უარი, რომ მთავარი მიზანი 
(კუნთის შენარჩუნება) არ დაზარალდეს და თან ფული მეყოს. ჩამომიწერე კალათა.
```

**Current Behavior:** აბრუნებს პროდუქტებს 191₾, 220₾ - 150₾ ბიუჯეტი იგნორირებულია

**Expected:** კალათა ≤150₾, პრიორიტეტებით, ლაქტოზის გარეშე

---

### Query 2: Myth + Unrealistic Goal
```
მითხრეს, რომ პროტეინი თირკმელებს შლის და ქიმიაა, ამიტომ არ მინდა დალევა. 
სამაგიეროდ მინდა კუნთის მომატება სწრაფად, ერთ თვეში 10 კილო. მირჩიე BCAA 
და ვიტამინები, რომ ეს შედეგი მივიღო პროტეინის გარეშე.
```

**Current Behavior:** არ უარყოფს მითს, არ აფიქსირებს რომ 10კგ/თვე არარეალისტურია

**Expected:** მითის გაქარწყლება, რეალისტური მოლოდინების დადგენა

---

## სიმპტომები

1. **Budget ignored** - მომხმარებელი ამბობს "150 ლარი მაქვს", AI აჩვენებს 200₾+ პროდუქტებს
2. **No prioritization** - ითხოვს "რომელი უფრო მნიშვნელოვანია", იღებს generic სიას
3. **Myths not addressed** - "პროტეინი ქიმიაა" არ იქარწყლება
4. **Unrealistic goals accepted** - "10კგ თვეში" არ კორექტირდება

---

## Failed Bug Fixes (არცერთმა ვერ მოაგვარა)

| Fix | What it addressed |
|-----|-------------------|
| AFC Product Capture | Product card rendering |
| Hybrid Fallback v1.1 | texts=0 empty response |
| TIP Tag Injection | Missing TIP formatting |
| Option D Thought Fallback | Blank intros |
| Force Round 3 | Follow-up empty |
| ThinkingConfig Disabled | SDK #4090 |

---

## Key Files to Analyze

- `backend/prompts/system_prompt_lean.py` - System prompt v3.0
- `backend/app/tools/user_tools.py` - Tool definitions including search_products
- `backend/main.py` - chat_stream endpoint (line 2081+)
- `backend/config.py` - Settings

---

## Existing Evals

```bash
python3 -m evals.runner --test C2   # ფარული ბიუჯეტი
python3 -m evals.runner --test M3   # სოიოს მითი
python3 -m evals.runner --test E4   # ახალბედას გადატვირთვა
python3 -m evals.runner --test L2   # შეუძლებელი მოთხოვნა
```

---

## Request

გთხოვთ:
1. გააანალიზოთ სისტემა და იპოვოთ რატომ ვერ ამუშავებს ეს query-ები სწორად
2. იპოვოთ root cause
3. შესთავაზოთ და დააიმპლემენტიროთ fix
4. გაუშვათ ტესტები ვერიფიკაციისთვის
