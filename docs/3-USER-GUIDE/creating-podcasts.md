# Creating Podcasts - Turn Research into Audio

Podcasts let you consume your research passively. This guide covers the complete workflow from setup to download.

---

## Quick-Start: Your First Podcast (5 Minutes)

```
1. Go to your notebook
2. Click "Generate Podcast"
3. Select sources to include
4. Choose a speaker profile (or use default)
5. Click "Generate"
6. Wait 3-10 minutes (non-blocking)
7. Download MP3 when ready
8. Done!
```

That's the minimum. Let's make it better.

---

## Step-by-Step: The Complete Workflow

### Step 1: Prepare Your Notebook

```
Before generating, make sure:

✓ You have sources added
  (At least 1-2 sources)

✓ Sources have been processed
  (Green "Ready" status)

✓ Notes are organized
  (If you want notes included)

✓ You know your message
  (What's the main story?)

Typical preparation: 5-10 minutes
```

### Step 2: Choose Content

```
Click "Generate Podcast"

You'll see:
- List of all sources in notebook
- List of all notes

Select which to include:
☑ Paper A (primary source)
☑ Paper B (supporting source)
☐ Old note (not relevant)
✓ Analysis note (important)

What to include:
- Primary sources: Always include
- Supporting sources: Usually include
- Notes: Include your analysis/insights
- Everything: Can overload podcast

Recommended: 3-5 sources per podcast
```

### Step 3: Choose Episode Profile

An episode profile defines the structure and tone.

**Option A: Use Preset Profile**

```
Open Notebook provides templates:

Academic Presentation (Monologue)
├─ 1 speaker
├─ Tone: Educational
└─ Format: Expert explaining topic

Expert Interview (2-speaker)
├─ 2 speakers: Host + Expert
├─ Tone: Q&A, conversational
└─ Format: Interview with expert

Debate Format (2-speaker)
├─ 2 speakers: Pro vs. Con
├─ Tone: Discussion, disagreement
└─ Format: Debate about the topic

Panel Discussion (3-4 speaker)
├─ 3-4 speakers: Different perspectives
├─ Tone: Thoughtful discussion
└─ Format: Each brings different expertise

Solo Explanation (Monologue)
├─ 1 speaker
├─ Tone: Conversational, friendly
└─ Format: Personal explanation
```

**Pick based on your content:**
- One main idea → Academic Presentation
- You want to explain → Solo Explanation
- Two competing views → Debate Format
- Multiple perspectives → Panel Discussion
- Want to explore → Expert Interview

### Step 4: Customize Episode Profile (Optional)

If presets don't fit, customize:

```
Episode Profile
├─ Title: "AI Safety in 2026"
├─ Description: "Exploring current approaches"
├─ Length target: 20 minutes
├─ Tone: "Academic but accessible"
├─ Focus areas:
│  ├─ Main approaches to alignment
│  ├─ Pros and cons comparison
│  └─ Open questions
├─ Audience: "Researchers new to field"
└─ Format: "Debate between two perspectives"

How to set:
1. Click "Customize"
2. Edit each field
3. Click "Save Profile"
4. System uses your profile for outline generation
```

### Step 5: Create or Select Speakers

Speakers are the "voice" of your podcast.

**Option A: Use Preset Speakers**

```
Open Notebook provides templates:

"Expert Alex"
- Expertise: Deep knowledge
- Personality: Rigorous, patient
- TTS: OpenAI (clear voice)

"Curious Sam"
- Expertise: Curious newcomer
- Personality: Asks questions
- TTS: Google (natural voice)

"Skeptic Jordan"
- Expertise: Critical perspective
- Personality: Challenges assumptions
- TTS: ElevenLabs (warm voice)

For your first podcast: Use presets
For custom podcast: Create your own
```

**Option B: Create Custom Speakers**

```
Click "Add Speaker"

Fill in:

Name: "Dr. Research Expert"

Expertise:
"20 years in AI safety research,
 deep knowledge of alignment approaches"

Personality:
"Rigorous, academic style,
 explains clearly, asks good questions"

Voice Configuration:
- TTS Provider: OpenAI / Google / ElevenLabs / Local
- Voice selection: Choose from available voices
- Accent (optional): British / American / etc.

Example:
Name: Dr. Research Expert
Expertise: AI safety alignment research
Personality: Rigorous, academic but accessible
Voice: ElevenLabs - professional male voice
```

### Step 6: Generate Podcast

```
1. Review your setup:
   Sources: ✓ Selected
   Profile: ✓ Episode profile chosen
   Speakers: ✓ Speakers configured

2. Click "Generate Podcast"

3. System begins:
   - Analyzing your content
   - Creating outline
   - Writing dialogue
   - Generating audio
   - Mixing speakers

4. Status shows progress:
   20% Outline generation
   40% Dialogue writing
   60% Audio synthesis
   80% Mixing
   100% Complete

Processing time:
- 5 minutes of content: 3-5 minutes
- 15 minutes of content: 5-10 minutes
- 30 minutes of content: 10-20 minutes
```

### Step 7: Review and Download

```
When complete:

Preview:
- Play audio sample
- Review transcript
- Check duration

Options:
✓ Download as MP3 - Save to computer
✓ Stream directly - Listen in browser
✓ Share link - Get shareable URL (if public)
✓ Regenerate - Try different speakers/profile

Download:
1. Click "Download as MP3"
2. Choose quality: 128kbps / 192kbps / 320kbps
3. Save file: podcast_[notebook]_[date].mp3
4. Listen!
```

---

## Understanding What Happens Behind the Scenes

### The Generation Pipeline

```
Stage 1: CONTENT ANALYSIS (1 minute)
  Your sources → What's the main story?
               → Key themes?
               → Debate points?

Stage 2: OUTLINE CREATION (2-3 minutes)
  Themes → Episode structure
        → Section breakdown
        → Talking points

Stage 3: DIALOGUE WRITING (2-3 minutes)
  Outline → Convert to natural dialogue
         → Add speaker personalities
         → Create flow and transitions

Stage 4: AUDIO SYNTHESIS (3-5 minutes per speaker)
  Script + Speaker → Text-to-speech
                  → Individual audio files
                  → High quality audio

Stage 5: MIXING & MASTERING (1-2 minutes)
  Multiple audio → Combine speakers
               → Level audio
               → Add polish
               → Final MP3

Total: 10-20 minutes for typical podcast
```

---

## Text-to-Speech Providers

Different providers, different qualities.

### OpenAI (Recommended)

```
Voices: 5 options (Alloy, Echo, Fable, Onyx, Shimmer)
Quality: Good, natural sounding
Speed: Fast
Cost: ~$0.015 per minute
Best for: General purpose, natural speech
Example: "I have to say, the research shows..."
```

### Google TTS

```
Voices: Many options, various accents
Quality: Excellent, very natural
Speed: Fast
Cost: ~$0.004 per minute
Best for: High quality output, accents
Example: "The research demonstrates that..."
```

### ElevenLabs

```
Voices: 100+ voices, highly customizable
Quality: Exceptional, very expressive
Speed: Slower (5-10 seconds per phrase)
Cost: ~$0.10 per minute
Best for: Premium quality, emotional range
Example: [Can convey emotion and tone]
```

### Local TTS (Free)

```
Voices: Limited, basic options
Quality: Basic, robotic
Speed: Depends on hardware (slow)
Cost: Free (local processing)
Best for: Privacy, testing, offline use
Example: "The research shows..."
Privacy: Everything stays on your computer
```

### Which Provider to Choose?

```
For your first podcast: Google (quality/cost balance)
For privacy-sensitive: Local TTS (free, private)
For premium quality: ElevenLabs (best voices)
For budget: Google (cheapest quality option)
For speed: OpenAI (fast generation)
```

---

## Tips for Better Podcasts

### Choose Right Profile

```
Single source analysis → Academic Presentation
  "Explaining one paper to someone new"

Comparing two approaches → Debate Format
  "Pros and cons of different methods"

Multiple sources + insights → Panel Discussion
  "Different experts discussing topic"

Narrative exploration → Expert Interview
  "Host interviewing research expert"

Personal take → Solo Explanation
  "You explaining your analysis"
```

### Create Good Speakers

```
Good Speaker:
✓ Clear expertise (know what they're talking about)
✓ Distinct personality (not generic)
✓ Good voice choice (matches personality)
✓ Realistic backstory (feels like real person)

Bad Speaker:
✗ Generic expertise ("good at research")
✗ No personality ("just reads")
✗ Mismatched voice (deep voice for young person)
✗ Contradicts personality (serious person uses casual voice)
```

### Focus Content

```
Better: Podcast on ONE specific topic
  "How transformers work" (15 minutes, focused)

Worse: Podcast on everything
  "All of AI 2025" (2 hours, unfocused)

Guideline:
- 5-10 minutes: One narrow topic
- 15-20 minutes: One broad topic
- 30+ minutes: Multiple related subtopics

Shorter is usually better for podcasts.
```

### Optimize Source Selection

```
Too much content:
  "Here are all 20 papers"
  → Podcast becomes 2+ hours
  → Unfocused
  → Low quality

Right amount:
  "Here are 3 key papers"
  → Podcast is 15-20 minutes
  → Focused
  → High quality

Rule: 3-5 sources per podcast
     Remove long background papers
     Keep focused on main topic
```

---

## Quality Troubleshooting

### Audio Sounds Robotic

**Problem**: TTS voice sounds unnatural

**Solutions**:
```
1. Switch provider: Try Google or ElevenLabs instead
2. Choose different voice: Some voices more natural
3. Shorter sentences: Very long sentences sound robotic
4. Adjust pacing: Ask for "natural, conversational pacing"
```

### Audio Sounds Unclear

**Problem**: Hard to understand what's being said

**Solutions**:
```
1. Re-generate with different speaker
2. Try different TTS provider
3. Use speakers with clear accents
4. Lower background noise (if any)
5. Increase speech rate (if too slow)
```

### Missing Content

**Problem**: Important information isn't in podcast

**Solutions**:
```
1. Include that source in content selection
2. Review generated outline (check before generating)
3. Regenerate with clearer profile instructions
4. Try different model (more thorough model)
```

### Speakers Don't Match

**Problem**: Speakers sound like same person

**Solutions**:
```
1. Choose different TTS providers (OpenAI + Google)
2. Choose very different voice options
3. Increase personality differences in profile
4. Try different speaker count (2 vs 3 vs 4)
```

### Generation Failed

**Problem**: "Podcast generation failed"

**Solutions**:
```
1. Check internet connection (especially TTS)
2. Try again (might be temporary issue)
3. Use local TTS (doesn't need internet)
4. Reduce source count (less to process)
5. Contact support if persistent
```

---

## Advanced: Multiple Podcasts from Same Research

You can generate different podcasts from one notebook:

```
Podcast 1: Overview
  Profile: Academic Presentation
  Sources: Papers A, B, C
  Speakers: One expert
  Length: 15 minutes

→ Use for "What's this about?" understanding

Podcast 2: Deep Dive
  Profile: Expert Interview
  Sources: Paper A (Full) + B, C (Summary)
  Speakers: Expert + Interviewer
  Length: 30 minutes

→ Use for detailed exploration

Podcast 3: Debate
  Profile: Debate Format
  Sources: Papers A vs B (different approaches)
  Speakers: Pro-A speaker + Pro-B speaker
  Length: 20 minutes

→ Use for comparing approaches
```

Each tells the same story from different angles.

---

## Exporting and Sharing

### Download MP3

```
1. Generation complete
2. Click "Download"
3. Choose quality:
   - 128 kbps: Smallest file, lower quality
   - 192 kbps: Balanced (recommended)
   - 320 kbps: Highest quality, largest file
4. Save to computer
5. Use in podcast app, upload to platform, etc.
```

### Export Transcript

```
1. Click "Export Transcript"
2. Get full dialogue as text
3. Useful for:
   - Blog post content
   - Show notes
   - Searchable text version
   - Accessibility
```

### Share Link

```
If podcast is public:
1. Click "Share"
2. Get shareable link
3. Others can listen/download
4. Useful for:
   - Sharing with team
   - Public distribution
   - Embedding on website
```

### Publish to Podcast Platforms

```
If you want to distribute (future feature):
1. Download MP3
2. Upload to platform (Spotify, Apple Podcasts, etc.)
3. Add metadata (title, description, episode notes)
4. Your research becomes a published podcast!
```

---

## Best Practices

### Before Generation
- [ ] Sources are processed and ready
- [ ] You've chosen content to include
- [ ] You have a clear episode profile
- [ ] Speakers are well-defined
- [ ] Content is focused (3-5 sources max)

### During Generation
- Don't close the browser (use background processing)
- Check back in 5-15 minutes
- Review transcript when complete
- Listen to sample before downloading

### After Generation
- [ ] Download MP3 to computer
- [ ] Save in organized folder
- [ ] Add metadata (title, description, date)
- [ ] Test listening in podcast app
- [ ] Share with colleagues for feedback

---

## Use Cases

### Academic Researcher
```
Podcast: Explaining your dissertation
Speakers: You + colleague
Content: Your papers + supporting research
Use: Share with advisors, test explanations
```

### Content Creator
```
Podcast: Research-to-podcast article
Speakers: Narrator + expert
Content: Articles you've researched
Use: Transform article into podcast version
```

### Team Research
```
Podcast: Weekly research updates
Speakers: Multiple team members
Content: This week's papers
Use: Team updates, knowledge sharing
```

### Learning/Teaching
```
Podcast: Teaching material
Speakers: Teacher + inquisitive student
Content: Textbook + examples
Use: Students learn while commuting
```

---

## Cost Breakdown Example

### Generate 15-minute podcast with ElevenLabs

```
Generation (outline + dialogue):
  No charge (included in service)

Text-to-speech:
  2 speakers × 15 minutes = 30 minutes TTS
  ElevenLabs: $0.10 per minute
  Cost: 30 × $0.10 = $3.00

Processing:
  Included (no additional cost)

Total: $3.00 per podcast

Cheaper options:
  With Google TTS: ~$0.12
  With OpenAI: ~$0.45
  With Local TTS: ~$0.00
```

---

## Summary: Podcasts as Research Tool

Podcasts transform how you consume research:

```
Before: Reading papers takes time, focus
After: Listen while commuting, exercising, doing chores

Before: Can't share complex research easily
After: Share audio of your analysis

Before: Different consumption styles isolated
After: Same research, multiple formats (read/listen)
```

Podcasts aren't just for entertainment—they're a tool for making research more accessible, shareable, and consumable.

That's why they're important for Open Notebook.
