# Rhode Island Hurricane — November 2026 backup

Saved October 23, 2026. This snapshot preserves the completed editorial draft and existing cover artwork.

## Start here

- [Read the complete Word manuscript](work/hurricane-first-issue/output/Rhode-Island-Hurricane-November-2026-Stories.docx)
- [Read the 19-page PDF proof](proof/Rhode-Island-Hurricane-November-2026-Stories.pdf)
- [Download the editorial package ZIP](work/hurricane-first-issue/output/Rhode-Island-Hurricane-November-2026-Editorial-Package.zip)
- [Copy the cover wording](work/hurricane-first-issue/output/Rhode-Island-Hurricane-Cover-Copy.txt)
- [Open the ten individual stories](work/hurricane-first-issue/output/Rhode-Island-Hurricane-November-2026/Stories)
- [Read the source register](work/hurricane-first-issue/output/Rhode-Island-Hurricane-November-2026/Sources.txt)
- [Read the editorial and cover handoff](work/hurricane-first-issue/output/Rhode-Island-Hurricane-November-2026/Editorial-Handoff.txt)

## Contents and status

The ten article drafts total 4,117 body words: Taylor Swift and Ashley Taunton, Jay Leno, Vinny Paz, Rhode Island's Meta lawsuit, the OpenAI–Hugging Face incident, Scialo Bros., Venda Ravioli, Matunuck Oyster Bar, Iggy's and the Florence music brief.

The Word manuscript and the individual text files in the output/Stories directory are the final edited text for this snapshot. Earlier Markdown drafts are retained under research as working history; use the edited output for publication decisions.

## Cover art

- [Original red-hood Record cover](cover-art/original-red-hood-record-cover.png)
- [Previously generated Taylor/Ashley Record cover](cover-art/taylor-swift-record-cover.png)

Both PNG files are preserved without alteration. They are existing Rhode Island Record artwork, not a completed Rhode Island Hurricane cover. The Hurricane portrait revision was blocked by the image service. The proposed Hurricane wording and layout instructions are complete and preserved in the handoff. The images are concept assets, not certified print-ready production files.

## Restore and rebuild

Download this branch using GitHub's Code → Download ZIP, or clone the repository and check out backup/rhode-island-hurricane-2026-10-23. Keep the folder structure intact.

To rebuild the editorial package, use Python with python-docx installed and run:

```sh
python3 work/hurricane-first-issue/build_package.py
```

The builder requires the sibling input work/ri-cover-story/article.json and the standalone cover-copy text file under work/hurricane-first-issue/output/. Both are included. The edit_food.py and edit_celebrities.py scripts are preserved as historical working scripts; they have already been applied and should not be rerun automatically.

## Verification and publication notes

MANIFEST.json records each preserved file's size, SHA-256 checksum and Git blob SHA. SHA256SUMS.txt provides a portable checksum list.

This is an editorial backup. The stories are drafts based on published sources, with source references and update notes. Matunuck's original dining-room reopening remains unconfirmed, and the Florence preview needs updating if published after the scheduled November 7 concert. No new interviews or tastings are represented as having occurred.
