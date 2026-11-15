# Motion Capture Source Licence Verification

**Document:** `docs/references/MOCAP_LICENSES.md`  
**Task:** T-007 mocap licence verification  
**Date:** 2026-11-15  
**Scope:** Legal and distribution audit of candidate motion capture libraries for the Plush animation pipeline.

---

## Executive Summary & Classification Matrix

| Source | Licensor / Entity | (a) Public GitHub Repo | (b) Published Videos | (c) Attribution Required | (d) Verdict | Primary Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ACCAD** | The Ohio State University | **YES** | **YES** | **YES** | **ALLOW** | CC BY 3.0 unported license explicitly permits redistribution and adaptation in any medium. |
| **CMU** | Carnegie Mellon University | **YES** | **YES** | **YES** | **ALLOW** | FAQ explicitly authorizes copying, modifying, and redistributing without permission; direct resale prohibited. |
| **Mixamo** | Adobe Inc. | **NO** | **YES** | **NO** | **LOCAL-ONLY** | Standalone file distribution prohibited; royalty-free for embedded media/videos. |
| **Rokoko** | Rokoko Electronics ApS | **NO** | **YES** | **Asset-dependent** | **LOCAL-ONLY** | Redistribution prohibited outside integrated digital media productions; account-bound license. |

### Verdict Definitions
- **ALLOW:** Converted clip files (`content/clips/*.clip.json`) may be committed directly to our public GitHub repository, used in animation production, and rendered into published videos.
- **LOCAL-ONLY:** Converted clip files may **never** be committed to the public Git repository (must be gitignored or kept on local storage). They may only be used locally by artists/developers to render and publish final video deliverables.
- **DENY:** Data cannot be used for our animation pipeline or video publishing.
- **UNCLEAR:** Ambiguous or contradictory terms requiring formal legal clarification before any ingestion.

---

## 1. ACCAD (The Ohio State University)

### 1.1 Source & Access Information
- **Institution:** Advanced Computing Center for the Arts and Design (ACCAD), The Ohio State University
- **Official Database URL:** [https://accad.osu.edu/research/motion-lab/mocap-system-and-data](https://accad.osu.edu/research/motion-lab/mocap-system-and-data) *(canonical; redirects from `https://accad.osu.edu/research/motion-lab/system-data`)*
- **Licence Terms URL:** [https://creativecommons.org/licenses/by/3.0/](https://creativecommons.org/licenses/by/3.0/)
- **Access Date:** 2026-11-15

### 1.2 Exact Licence / Terms Text
From the official ACCAD MoCap System and Data page:
> "The area below contains sample motion capture data to download plus useful scripts. The data is provided in three different formats. They are \*.amc/\*.asf, \*.c3d, \*.tvd, \*.txt. All files are stored zipped. Sample movies are 320x260."
>
> "Open Motion Project by ACCAD/The Ohio State University is licensed under a Creative Commons Attribution 3.0 Unported License."

From the Creative Commons Attribution 3.0 Unported (CC BY 3.0) Deed:
> "You are free to:
> - **Share** — copy and redistribute the material in any medium or format
> - **Adapt** — remix, transform, and build upon the material for any purpose, even commercially.
>
> Under the following terms:
> - **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.
> - **No additional restrictions** — You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits."

### 1.3 Classification for Our Use
- **(a) May converted clips be committed to a PUBLIC GitHub repository:** **YES**.  
  CC BY 3.0 permits redistribution and sharing in any medium or format, including converted formats (e.g. `plush.clip/1` JSON).
- **(b) May they be used in published videos:** **YES**.  
  CC BY 3.0 permits adaptation and use for any purpose, non-commercial and commercial.
- **(c) Required attribution:** **YES**.  
  Must credit: *"Open Motion Project by ACCAD/The Ohio State University"*, include a link to the license (`https://creativecommons.org/licenses/by/3.0/`), and note whether changes/conversions were made.
- **(d) Verdict:** **ALLOW**  
  **Reasoning:** Explicitly licensed under CC BY 3.0, a standard permissive open license compatible with public open-source Git hosting and public video publishing.

---

## 2. CMU Graphics Lab Motion Capture Database

### 2.1 Source & Access Information
- **Institution:** Carnegie Mellon University (CMU) Graphics Lab
- **Official Database URL:** [http://mocap.cs.cmu.edu/](http://mocap.cs.cmu.edu/)
- **Official FAQs URL:** [http://mocap.cs.cmu.edu/faqs.php](http://mocap.cs.cmu.edu/faqs.php)
- **Official Resources URL:** [http://mocap.cs.cmu.edu/resources.php](http://mocap.cs.cmu.edu/resources.php)
- **Access Date:** 2026-11-15

### 2.2 Exact Licence / Terms Text
From the official Home page (`http://mocap.cs.cmu.edu/`):
> "Welcome to the Carnegie Mellon University Motion Capture Database! This dataset of motions is free for all uses."
>
> "This data is free for use in research projects.
> You may include this data in commercially-sold products, but you may not resell this data directly, even in converted form.
> If you publish results obtained using this data, we would appreciate it if you would send the citation to your published paper to jkh+mocap@cs.cmu.edu, and also would add this text to your acknowledgments section:
> The data used in this project was obtained from mocap.cs.cmu.edu.
> The database was created with funding from NSF EIA-0196217."

From the official FAQs page (`http://mocap.cs.cmu.edu/faqs.php`):
> "**How can I use this data?**
> The motion capture data may be copied, modified, or redistributed without permission."

From the official Resources page (`http://mocap.cs.cmu.edu/resources.php`):
> "**Conversion of our Data into Other Formats:**
> These external links are provided for your convenience; we have NOT downloaded or tested these files ourselves.
> Bruce Hahn has converted our data into MotionBuilder-friendly bvh, and 3dsMax-friendly bvh; they are hosted at cgspeed. Wow, thanks Bruce for your incredible work!
> Mojo has converted Bruce's bvhs into Poser-friendly bvh. The dataset is here. Thanks Mojo!
> Jennifer Sumbu Longe has converted our data, and mocapclub's, into six other formats: .dae (Collada), .mb (Maya), .max (3ds Max), .vns (iClone), .bvh (iClone), and .fbx (Motion Builder, Maya, 3d Max, Modo,...)...
> IAFilm Productions at the Manukau Institute of Technology is using our mocap in short films. They have converted some clips to Carrara NLA. Their work is here. Their movie 'The House of Seville', built with a combination of keyframing and our mocap, was selected to run in the Philadelphia International Film Festival. Congrats!"

### 2.3 Analysis of Conflict & Redistribution FAQ
Early secondary discussions online noted an apparent tension between:
1. The Home page restriction: *"you may not resell this data directly, even in converted form."*
2. Public redistribution of converted assets.

The official FAQ directly resolves any ambiguity:
- **Redistribution Right:** The FAQ explicitly states: *"The motion capture data may be copied, modified, or redistributed without permission."*
- **Scope of Prohibition:** The prohibition is solely against *commercial direct resale* of the data itself (e.g. packaging the mocap into a paid asset store item or selling the converted raw files).
- **Public & Converted Distributions:** Converting CMU takes into new formats (such as Bruce Hahne's BVH conversions hosted at cgspeed) and distributing them free of charge is not only permitted without permission, but explicitly praised and linked from CMU's own official Resources page.
- Distributing converted motion clips in a public, free, open-source repository carries zero commercial resale fee and complies fully with both the Home page and the FAQs.

### 2.4 Classification for Our Use
- **(a) May converted clips be committed to a PUBLIC GitHub repository:** **YES**.  
  Explicitly allowed by the FAQ (*"may be copied, modified, or redistributed without permission"*), provided the files are distributed freely and not sold directly.
- **(b) May they be used in published videos:** **YES**.  
  Explicitly allowed (*"free for all uses"*, *"You may include this data in commercially-sold products"*, and film productions are explicitly recognized).
- **(c) Required attribution:** **YES**.  
  Must include in project documentation/acknowledgments:  
  *"The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217."*  
  *(If academic publications arise, citation must be sent to `jkh+mocap@cs.cmu.edu`).*
- **(d) Verdict:** **ALLOW**  
  **Reasoning:** The FAQ provides unambiguous permission to copy, modify, and redistribute the data without prior permission. Public GitHub hosting without direct resale is fully compliant.

---

## 3. Mixamo (Adobe)

### 3.1 Source & Access Information
- **Entity:** Adobe Inc.
- **Official Mixamo FAQ URL:** [https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html)
- **Adobe General Terms of Use URL:** [https://www.adobe.com/legal/terms.html](https://www.adobe.com/legal/terms.html)
- **Access Date:** 2026-11-15

### 3.2 Exact Licence / Terms Text
From the official Adobe Help Center Mixamo FAQ (`https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html`):
> "**Can I use both characters and animations commercially?**
> Yes. The characters and animations can be used royalty-free for personal, commercial, and non-profit projects. You can use them to:
> - Create video games
> - Create films and videos
> - Incorporate characters into illustrations and graphic art
> - 3D print characters"
>
> "**Can I sell a game with Mixamo characters?**
> Yes! You can use Mixamo characters and animations in a commercial video game. However, you cannot resell or distribute the raw character and animation files. Users should get Mixamo content from Mixamo, not from your project."
>
> "**Do I need to pay royalties or give credit?**
> No, you do not need to pay royalties or give credit to Adobe or Mixamo. Attribution is not required."

From the Adobe General Terms of Use (`https://www.adobe.com/legal/terms.html`):
> "You may reproduce and distribute Content Files only in connection with your End Use, however, under no circumstances can you distribute the Content Files on a stand-alone basis, outside of the End Use."

### 3.3 Classification for Our Use
- **(a) May converted clips be committed to a PUBLIC GitHub repository:** **NO**.  
  Adobe strictly prohibits distributing character or animation files on a standalone basis where third parties can obtain the assets directly (*"you cannot resell or distribute the raw character and animation files. Users should get Mixamo content from Mixamo, not from your project"*; *"under no circumstances can you distribute the Content Files on a stand-alone basis"*). Committing converted `.clip.json` clips directly into a public repository distributes standalone motion assets outside of an integrated, compiled application.
- **(b) May they be used in published videos:** **YES**.  
  Publishing rendered films, videos, or animations is explicitly listed as a permitted royalty-free commercial and personal use.
- **(c) Required attribution:** **NO**.  
  Attribution is not required (*"No, you do not need to pay royalties or give credit to Adobe or Mixamo. Attribution is not required"*), though permitted.
- **(d) Verdict:** **LOCAL-ONLY**  
  **Reasoning:** Converted Mixamo clips cannot be committed to a public GitHub repository without violating Adobe's redistribution clause. However, artists/developers may convert and use Mixamo animations on local machines to render scenes and publish the resulting video media.

---

## 4. Rokoko (Free / Marketplace Libraries)

### 4.1 Source & Access Information
- **Entity:** Rokoko Electronics ApS
- **Official Terms of Use URL:** [https://www.rokoko.com/terms-of-use](https://www.rokoko.com/terms-of-use) *(Effective date: 16 July 2026, Version 2.0.1)*
- **Official Website Terms of Service URL:** [https://www.rokoko.com/terms-of-service](https://www.rokoko.com/terms-of-service)
- **Official Motion Library / Assets URL:** [https://www.rokoko.com/products/motion-library](https://www.rokoko.com/products/motion-library)
- **Access Date:** 2026-11-15

### 4.2 Exact Licence / Terms Text
From Rokoko Services - Standard Terms of Use (`https://www.rokoko.com/terms-of-use`):

**Section 5: ROKOKO ASSETS**
> "**5.1** The license to use the Services includes a license to access and use the assets provided/made available by us as part of the Services (“Rokoko Assets”). Rokoko Assets can be both sample data/assets produced and owned by us as well as Motion Library Assets owned by third parties. The license to each Rokoko Asset is limited to the period in which you have an Account. Unless otherwise stated, the definition of \"Services\" in the Terms also covers/includes Rokoko Assets."
>
> "**5.2** The Services permit you to collaborate with other End Users, including sharing Rokoko Assets (and User Content) between Rokoko Teams (as such Rokoko Teams are used and defined in/by use of the Services). You represent and warrant to always respect the rights in and license terms of any Rokoko Assets (and/or User Content) purchased, shared by/with you, or otherwise used with/in the Services."
>
> "**5.3** You may download and make copies of the Rokoko Assets for legitimate purposes, including back-up purposes, subject to the Terms. In addition, we acknowledge that copies of the Rokoko Assets may be made when the Rokoko Assets have been integrated as part of digital media productions. Unless expressly provided for in the license terms of the specific Rokoko Asset, you may not reproduce, distribute, sublicense, rent, lease or lend any Rokoko Asset other than as follows from the above."
>
> "**5.4** You may not use any assets obtained or provided under this agreement for the purpose of developing, training, or enhancing machine learning and/or AI models or algorithms, whether for commercial or non-commercial purposes, without the explicit written consent of the Company."

**Section 4.2 & 6.2:**
> "**4.2** All software and software-as-a-service (SaaS) used in connection with the Services (\"Software\") is proprietary to us or to third parties, and any use, redistribution, sale, de-compilation, reverse engineering, disassembly, translation, or reduction of the Software is prohibited. The Software is licensed, not sold."
>
> "**6.2** All title and intellectual property rights in and to the Services (including Software, images, photographs, animations, graphics, 3D graphics, video, audio, music, text, and tutorials incorporated into the Services), the accompanying printed materials, and any copies of the Services, are owned by us. All rights not expressly granted are reserved by us."

### 4.3 Classification for Our Use
- **(a) May converted clips be committed to a PUBLIC GitHub repository:** **NO**.  
  Section 5.3 explicitly bans distribution outside of integrated digital media productions: *"you may not reproduce, distribute, sublicense, rent, lease or lend any Rokoko Asset other than as follows from the above."* Committing converted clips to a public GitHub repo is unauthorized standalone distribution. Additionally, Section 5.1 restricts asset licensing to the duration of an active user account.
- **(b) May they be used in published videos:** **YES**.  
  Section 5.3 explicitly acknowledges: *"copies of the Rokoko Assets may be made when the Rokoko Assets have been integrated as part of digital media productions."* Published animation videos constitute digital media productions.
- **(c) Required attribution:** **Asset-dependent**.  
  The general Terms of Use do not prescribe attribution for Rokoko sample assets; however, third-party Motion Library marketplace assets have vendor-specific licenses whose terms must be respected per Section 5.2.
- **(d) Verdict:** **LOCAL-ONLY**  
  **Reasoning:** Redistribution of standalone or converted assets via a public Git repository is strictly prohibited by Section 5.3. Rokoko assets may only be used locally on developer workstations to produce integrated digital media productions (rendered videos). Furthermore, Section 5.4 strictly forbids using Rokoko assets to train or develop ML/AI models.

---

## 5. Pipeline Integration & Repository Rules

To keep the repository clean and legally compliant:

1. **Permitted in Repository (`content/clips/*.clip.json`):**
   - **ACCAD clips:** Fully allowed. Must include metadata: `license: "CC-BY-3.0"` and `attribution: "Open Motion Project by ACCAD/The Ohio State University"`.
   - **CMU clips:** Fully allowed. Must include metadata: `license: "CMU-Mocap"` and `attribution: "The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217."`

2. **Prohibited in Repository (Local / Working-Copy Only):**
   - **Mixamo clips:** Must NOT be committed. If used locally, store in a local gitignored path (e.g. `content/clips/local_only/` or ignored file prefix).
   - **Rokoko clips:** Must NOT be committed. Stored strictly in local gitignored paths for rendering video productions.

3. **Clip Metadata Schema Requirement:**
   When mocap conversion scripts generate `plush.clip/1` clips (`docs/ANIMATION_CLIPS.md` §8), the converter must populate:
   ```json
   {
     "type": "plush.clip/1",
     "source": "mocap",
     "license": "CC-BY-3.0",
     "attribution": "Open Motion Project by ACCAD/The Ohio State University"
   }
   ```
