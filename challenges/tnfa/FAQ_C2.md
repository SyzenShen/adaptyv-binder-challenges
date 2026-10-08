# Challenge 2 (TNF-α) — Questions & Answers Reference

> **Source:** Official Proteinbase Challenge-2 page snapshot, fetched 2026-10-08
> (`challenges/tnfa/data/proteinbase_c2_page_2026-10-08.txt`). The organizers state
> they expect to update the FAQ throughout the competition, so re-verify details on
> the live page before relying on them. Items the repository marks as USER_REPORTED
> are flagged below and must be re-checked against the live page.

---

## Challenge 2 at a glance

**Target.** Human TNF-α (Tumor necrosis factor). Design against the soluble,
trimeric form. TNF-α signals as a trimer, with three receptor-binding sites where
its subunits meet; each target is presented as a trimer, so there are three copies
of the epitope per target.

- Human reference: UniProt **P01375-1**, target residues **77–233** (157 aa);
  assay construct **TNA-H4211**, tag-free.
- Structure reference: **PDB 1TNF**, chains A–C (apo human trimer).
- Recommended epitope: the **receptor-binding site at the interface between two
  adjacent protomers** — the same site targeted by the therapeutic antibodies
  adalimumab and infliximab.
- Mouse construct: the mouse sequence is **not given on the page**. The two soluble
  domains are 79% identical (124 of 156 aligned residues). The mouse sequence omits
  the C-terminal polyhistidine tag carried by the assay construct. Both constructs
  are supplied as trimers (SEC-MALS: about 45–62 kDa human, 50–65 kDa mouse).

**Three design objectives** (all accounted for when selecting the best designs):

1. **Binding affinity** — design a binder against human TNF-α; affinity is measured
   using the soluble trimeric form of human TNF-α.
2. **Mouse cross-reactivity** — the same design should recognize both human and
   mouse TNF-α; mouse binding is tested at pH 7.4.
3. **pH-selective binding** — the binder must bind human TNF-α at pH 7.4 and show
   **no detectable binding at pH 6.0**. pH 7.4 replicates blood plasma; pH 6.0
   approximates the acidifying early endosome, where a binder that releases TNF-α
   allows the target to be cleared and the binder to be reused (an approach used to
   make antibody drugs longer-lasting). Binding is measured against human TNF-α in
   both in vitro conditions (pH 7.4 and pH 6.0).

**How designs are ranked** (per the page and FAQ 3, in priority order):

1. **pH-selective binding** — binds TNF-α at pH 7.4 but shows no detectable binding
   at pH 6.0.
2. **Mouse cross-reactivity** — the same sequence binds mouse TNF-α as well as human.
3. **Affinity** — affinity against human TNF-α.

The organizers note (FAQ 3) that pH-sensitive binder design is generally much harder
than designing high-affinity binders, so a weak but clearly pH-sensitive binder may
be considered more impactful than a high-affinity binder that is not pH-sensitive;
they will be mindful of these challenge-specific difficulties when selecting winners.

> **CRITICAL — pH mechanism is NOT stated.** The snapshot does **not** state any
> molecular mechanism for the pH switch. The required behavior (bind at pH 7.4, no
> detectable binding at pH 6.0) is a measured outcome only. Do **not** claim or infer
> a pH-switching mechanism from inter-residue distances, Rosetta energies, or MPNN
> scores. Any mechanistic hypothesis (e.g. interface histidines) is a hypothesis to
> test experimentally, not a stated rule.

**Submission requirements.**

- **Length:** 10–250 amino acids.
- **Format:** single chain protein, nanobody, scFv, or Fab.
- **Designs per participant:** up to 40 for Track 1; up to 20 for Tracks 2 and 3.
- **Design type:** de novo designs only.
- **Submission file:** a CSV ordered by your ranking (top row = highest). Required
  columns at minimum: `name` (unique identifier) and `sequence`; plus `molecule_class`
  (one of `protein`, `nanobody`, `scfv`, `fab_kappa`, `fab_lambda`). Fabs are submitted
  as a single sequence with VH followed by VL separated by a `:` (`{VH}:{VL}`).

**Hard filters** (FAQ 8). Designs must: meet the protein length and
"nanobodyness/antibodyness" criteria of FAQs 1 and 2; be unique (no duplicate
submissions); and be **de novo and zero-shot** — not relying on an initial binder as
a starting point, and having adequate sequence and structural diversity (CDR
sequence-diversity for nanobodies/antibodies) from known proteins. You may not take
an existing binder and modify it; designs must be produced from scratch. Known binders
may still be used to calibrate/evaluate filtering metrics or to fine-tune/train models.

**Submission deadline.**

- **Challenge 2: Sunday, October 11, 2026, 23:59 Anywhere on Earth (AoE, UTC−12).**
  Stated on the page ("Submissions are open until Sunday, October 11, 23:59 AoE") and
  in FAQ 6. **(USER_REPORTED — re-verify on the live page.)** The repo notes this
  corresponds to 2026-10-12 11:59 UTC.

---

## Frequently Asked Questions

> The organizers recommend providing this FAQ list to your Claudes and expect to
> update it throughout the competition as more FAQs emerge. The 20 questions below
> reproduce the snapshot in order.

### 1. What classes of molecules can be designed and submitted?

De novo proteins (including minibinders, larger proteins, and microbinders),
nanobodies, and antibodies can be submitted. Importantly:

- For single chain proteins, the minimum length is **10 amino acids** and the maximum
  length is **250 amino acids**.
- For nanobodies/antibodies, a design is considered a nanobody/antibody if it is
  annotated as such by a tool like **ANARCI**. Participants who seek to design
  nanobodies and antibodies are advised to use common framework regions as a starting
  point. For scFvs, the organizers may reformat to their preferred linker.

### 2. How will different classes of molecules be evaluated?

Performance will be stratified into **five molecule categories**:

- **Protein minibinders:** proteins of between 40 and 100 amino acids (inclusive).
- **Large protein binders:** proteins of >100 amino acids.
- **Protein microbinders:** proteins of <40 amino acids.
- **Nanobodies.**
- **Antibodies** (formatted as either scFv or Fab — see Question 5).

### 3. What criteria will be used to determine the winners of the competition?

The challenges are multivariable, making it difficult to define a single metric for
success. The organizers expect to announce winners across categories within
challenges. For example, for the challenge of designing a mouse cross-reactive,
pH-sensitive binder against a human target, winners could be announced for each of:

- **Highest affinity human binder** against a functional epitope.
- **Most mouse cross-reactive binder**, measured for example using mouse affinity
  (with human affinity above a threshold).
- **Most pH-sensitive binder**, measured for example using the ratio of affinities at
  different pH values (with affinity above a threshold).
- **Most pH-sensitive, mouse cross-reactive binder**, measured using a combination of
  the above criteria.

The primary goal of the competition is to show frontier protein design capabilities,
and this will be taken into account when assessing winning designs. For example,
pH-sensitive binder design is generally much harder than designing high-affinity
binders, so a weak but clearly pH-sensitive binder may be considered more impactful
than a high-affinity binder that is not pH-sensitive. The organizers will be mindful
of these challenge-specific difficulties when selecting winners. Another goal is to
demonstrate therapeutic relevance, so participants are recommended to target
functional epitopes.

### 4. How many designs should I submit?

If you are part of **Track 1**, you should submit **at least 20 and at most 40**
designs. If you are part of **Tracks 2 or 3**, you should submit **at most 20** designs.

### 5. How and where should I submit my designs? Should I submit any additional information with my designs? Can I submit anonymously?

Submit your designs as a **CSV ordered by how you would rank your molecules** (top row
higher) with, at minimum, the following columns:

- `name`: a unique identifier.
- `sequence`: the sequence of the designed protein.
  - For **Fabs**, submit as a single sequence with VH followed by VL separated by a
    `:` (e.g. `{VH}:{VL}`). Use `molecule_class` to indicate whether you intend the
    light chain to be kappa or lambda.
- `molecule_class`: one of `protein`, `nanobody`, `scfv`, `fab_kappa`, `fab_lambda`.

Participants are encouraged to submit as much information as they are comfortable
sharing, including metrics (e.g. ipTM, ipSAE, self-consistency, physics-based metrics,
sequence liability scores), structure models from design and folding models, and
methodologies (e.g. AI models, design models, folding models, strategies, provenance
on how designs were generated). Participants are welcome to upload data to a shared
repository (e.g. Google Drive, GitHub) and provide a link with their submission. One
option is to ask your Claudes to write a methods paper and create a metadata package
for submission. **All data and methodology submitted may be made publicly available.**

As described in FAQ 8, for **Tracks 2 and 3** the additional information you submit is
provided to Claude to help select designs; with more information Claude can make more
informed decisions. **Any use of embedded instructions or prompt injection may be
deemed grounds for disqualification.**

You can submit anonymously by making an anonymous Proteinbase account. If you later
choose to deanonymize, you can (see FAQ 11). Submit from the page of the challenge you
are entering, linked from the challenges list.

### 6. When will problems be released? When should I submit my designs?

The organizers expect to release one problem every week on Monday at approximately
**9:00 AM PDT**, starting September 28th, 2026 and ending October 26th, 2026. For each
problem, participants have until **23:59 Anywhere on Earth (AoE, UTC−12)** on its
closing day to submit designs. Deadlines:

- **Challenge 1:** Wednesday, October 7.
- **Challenge 2:** Sunday, October 11.
- **Challenge 3:** Sunday, October 18.
- **Challenge 4:** Sunday, October 25.
- **Challenge 5:** Sunday, November 1.

### 7. How many designs will be screened?

Per problem, the organizers expect to screen **~1500 designs** (50% for Track 1, 25%
for Track 2, and 25% for Track 3).

### 8. How will you select which designs are screened?

There are hard criteria/filters used for all designs:

- They must meet the criteria of FAQs 1 and 2 for protein length and
  "nanobodyness/antibodyness". They must also be **unique** (don't submit the same
  design multiple times).
- They must be **de novo and zero-shot**, defined as not having relied on an initial
  binder as a starting point and having adequate sequence- and structural-diversity
  (CDR sequence-diversity for nanobodies/antibodies) from known proteins. You may not
  take an existing binder and modify it; designs must be produced from scratch. You
  are encouraged to otherwise use any data available to you — for example, you may
  take known binders and use them to evaluate/calibrate design filtering metrics or to
  fine-tune/train models. The organizers recommend reading Adaptyv's latest blog post
  on novelty.

Beyond the hard criteria, designs will be selected as follows:

- For **Track 1** participants, their **top 20 designs that pass filtering** will be
  screened. Track 1 participants are encouraged to send sequences already ordered by
  the ranking method they (preferably) describe in their methods.
- For **Track 2 and 3** participants, all submitted designs are pooled together along
  with submitted information and provided to Claude along with a **design selection
  prompt written in advance by Anthropic and Adaptyv**. The prompt makes selections
  based on predicted design quality and novelty, as well as method novelty. Per
  problem, a total of **~375 designs** will be selected for each of Tracks 2 and 3.

The selection prompt will **not** be shared in advance, to avoid teams over-optimizing
metrics that may or may not correlate with good designs. Given the diversity of
challenges and the fact that most metrics do not account for the set conditions (e.g.
pH-sensitivity), this avoids the final selection being biased by a single metric.
Participants are encouraged to submit the designs they think will fare best in each
challenge, in a ranked order according to their preference or the ranking method they
(preferably) describe in their methods.

### 9. How will I know if my designs were selected for screening?

Once designs have been selected for a problem and DNA has been ordered, a **Collection**
will be released on Proteinbase containing the selected designs. The organizers
estimate this Collection will be available **about one week after the final competition
challenge**.

### 10. How do I submit my designs?

You'll first need to create a **Proteinbase account** (either an individual one or one
for your team). Then you can directly submit a CSV with your sequences and fill in the
submission form with your workflow details.

### 11. What if I want to submit anonymously?

This is allowed; you'll only need to create an anonymous Proteinbase account. It is
highly recommended to reveal your identity/company/university afterwards, but the
organizers understand there are circumstances where this would not be possible.

### 12. What experimental data will be generated? When and how will experimental data be released?

This competition measures binding and affinity, but with twists. In addition to
binding against the human target, for some targets they plan to measure binding in
acidic pH environments as well as against orthologs to measure cyno/mouse
cross-reactivity. For the peptide-MHC complex they will screen against relevant
off-targets. For the GPCR they only plan to screen for binding at this time. Specific
conditions per challenge are communicated on each challenge's competition page once it
is launched.

Data will be released on Proteinbase. The organizers hope to complete experimental
validation for each problem **approximately one month after the submission window
closes**. The first set of data will be released in **early November 2026**.
Experimental validation — especially for challenging problems — can face unexpected
challenges and require re-runs to gain confidence; any possible delays will be
communicated to participants in the Proteinbase Slack channel.

### 13. Do I have to use Claude? Can I use other AI tools?

While participants are strongly encouraged — especially those in Tracks 1 and 2 — to
use Claude, you may use other AI tools. Any AI tools or design models used can be
disclosed in the submission form.

### 14. What happens to unused Claude or Modal credits after the competition?

Unused credits expire at the end of the competition. Claude Max plans will expire
**approximately three months after the competition begins**. The organizers want to
see what participants can do with this compute, so they encourage its use.

### 15. What tools and resources may I use for design?

Neither Anthropic nor Adaptyv seek to impose additional restrictions on tools that can
be used. As long as you can access the tool appropriately (e.g. you are not violating
licenses), you may use it. You may use externally available tools such as open-source
folding and design models, or internal-only tools. For any commercially-licensed tools
(e.g. **Rosetta**), the organizers require that you own that specific license
beforehand. In addition to the Claude and Modal credits provided, you may use any
other resources (e.g. in-house GPU clusters) you have access to.

### 16. Who owns the IP for all designs and validated sequences?

All validated sequences and experimental results will be released publicly on
Proteinbase, which is under an **ODC-BY license**. Submitted designs that were not
selected or validated but are in a public Proteinbase Collection are still under the
same ODC-BY license. Additional details on publication can be found in Section 6 of
the Official Competition Terms.

### 17. Should I disclose any proprietary methods or tools?

The organizers recommend that all participants describe in detail the methods and
tools they are using, linking to any papers, articles, or technical reports they based
their work on. These details will be used when selecting designs to be validated,
ensuring novel methods without prior experimental validation are fairly represented.
This information will be made public in the Proteinbase Collection, so the organizers
understand if there are details participants would prefer not to disclose (e.g. a
proprietary tool).

### 18. How will the data generated in this competition be used by Anthropic and Adaptyv?

The goal of the competition is to advance the field of protein design, so data and
methodology generated and shared during the competition will be made publicly
available on Proteinbase and accessible broadly for downstream uses. This was done
previously with the RBX1 competition. Inputs to and outputs from Claude will be
governed by the Terms of Service applicable to the participant's Anthropic account.

### 19. Are there any resources you recommend we review?

Some resources the teams point to:

- **Adaptyv's blog**, which includes posts about protein design, past competitions,
  and experimental validation, as well as the **EGFR competition post-analysis paper**.
- **Proteinbase**, which hosts a large corpus of protein design data, including from
  past competitions.
- **Anthropic's blog post on protein design**, which covers Claude's ability to design
  de novo protein binders (technical report; experimental data for the protein design
  campaign).
- **Anthropic's blog post on uplifting biomolecular modeling**, which includes
  inference-optimized versions of popular open-source protein folding and design
  models (code; technical report).

The organizers strongly recommend using the inference-optimized models to maximize GPU
compute, and reviewing the significantly simplified binder design prompt in the
technical report.

### 20. What if I have more questions?

Join the organizers on the **Proteinbase Slack channel**.
