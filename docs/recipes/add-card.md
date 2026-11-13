# Add a card to the Proxy page

The Proxy page is a grid (3x2 landscape, 2x3 portrait). Group tiles fill it first, then the System card, then the Messages card, each taking the next free cell. A new card takes the cell after those. Cards get a rectangle `(x, y, w, h)` from the grid and draw inside it, so they stretch with the screen.

Files: `firmware/AIUsageMonitor/ui.cpp` only (plus `model.*` if the card needs new data; see [add a data source](add-data-source.md)).

Log this edit in `docs/MY_CHANGES.md`.

**Before you start:** you need the `my-setup` branch, `profiles/my.json` and `docs/MY_CHANGES.md`. If any is missing, do steps 2 to 4 of [customise safely](customise-safely.md) first.

## Steps

1. **Read the model card.** Open `ui.cpp` and read `drawProxySystem` (about 20 lines). It is the smallest complete card: it fills a rounded rectangle, draws a title, then draws rows whose height comes from `h`.
2. **Write your card.** Add a function above `drawProxy`, with a forward declaration near the top beside the others:

   ```cpp
   static void drawProxyMine(int x, int y, int w, int h) {
     TFT_eSPI& g = G();
     g.fillRoundRect(x, y, w, h, 5, C_PANEL);
     text("MY CARD", x + 6, y + 2, 2, C_TEXT);
     // Two rows below the title. Derive every position from x, y, w, h.
     const char* labels[] = {"Up", "Ver"};
     const char* values[] = {"--", "1"};   // "--" is unknown, never 0
     const int rowH = (h - 21) / 2;
     for (int i = 0; i < 2; i++) {
       const int ry = y + 21 + i * rowH;
       text(labels[i], x + 6, ry, 1, C_MUTED);
       text(values[i], x + w - 6, ry, 2, C_TEXT, TR_DATUM);
     }
   }
   ```

   Replace the labels and values with your own; add rows by growing both arrays and dividing by the new count.

   Rules: colours come from the `C_*` names (`C_TEXT`, `C_MUTED`, `C_PANEL`, `C_GREEN`, `C_RED`). Never hard-code a pixel width or height of the screen; use `w`, `h`, and `W`/`H`. Show `--` for unknown values, never `0`.
3. **Place it.** In `drawProxy`, after the line that places Messages, add:

   ```cpp
   if (place(1, cell)) drawProxyMine(pad + (cell % cols) * (cw + gap), top + (cell / cols) * (ch + gap), cw, ch);
   ```

   If all six cells are full the card is simply skipped. To make room, remove the System or Messages line, or raise `cols`/`rows` (and check the card text still fits; see [resize](resize-display.md)).
4. **Build.** `.\scripts\build.ps1 -Profile my`. Fix the first error and rebuild. Check: the output contains a `build ok` line. It is not the last line; compiler warnings (such as `TOUCH_CS pin not defined`) and the size report follow it and are expected. If it reports `profile error` for `profiles\my.json`, do step 3 of [customise safely](customise-safely.md).
5. **Flash and look.** `.\scripts\flash.ps1`, then `python scripts\screenshot.py --feed --out build\card.png`. Open the image. Check: the card is in its cell, text does not touch the edges, nothing overlaps.
6. **Check portrait.** Build once with `-Rotation 0`, capture again, and confirm the card still fits. Rebuild without the override afterwards.
7. **Commit** on `my-setup` and add the ledger row.

## Common mistakes

- Drawing past `x + w` or `y + h`: the card is small (about 100x90 px). Use font 1 for labels and font 2 for values.
- Forgetting the forward declaration: the compiler reports an undeclared identifier.
- Using the same cell as another card: always go through `place()`.
