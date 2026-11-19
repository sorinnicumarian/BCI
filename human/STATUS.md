# Status

**Last update:** 2026-11-20

- Current best: 4-class EEG+EOG mouse control, ~65% accuracy (ds06); binary SVM 75.5% (ds09)
- Being tried: <...>
- Decisions needed: <...>

## Todo
- [ ] Epoc X + agent AI (nota 8, fezabil pana pe 14 dec). Un BCI are latime de banda mica, deci il folosesti doar ca sa alegi: agentul propune 3-4 actiuni, iar tu alegi cu mintea. Il legi de Claude printr-un server MCP. Emotiv expune datele printr-un Cortex API pe WebSocket, iar concurentii au deja suport nativ MCP livrat prin update-uri over-the-air, deci directia e de actualitate.
  - [ ] https://docs.rs/crate/emotiv/0.0.8/source/README.md
  - [ ] https://neurosity.co/guides/neurosity-crown-vs-emotiv-epoc-x#subscribe-to-newsletter
