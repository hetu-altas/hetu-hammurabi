
# Inherited Cordis API [​](#inherited-cordis-api)


The framework `ctx` members and events every plugin sees beyond the harness tier — pinned vendor source ([vendoring policy](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/README.md)), summarized tersely so the harness pages stay focused on repository-owned vocabulary. Detailed Context, Fiber, Registry, and Service APIs are generated in [context.md](./context), [fiber.md](./fiber), [registry.md](./registry), and [service.md](./service); the event-dispatch methods in [events.md](./events).


This file is GENERATED from source (`scripts/gen-cordis-catalog.ts`) and verified fresh by `pnpm run verify-cordis-catalog` (part of `doc-sync`) — do not edit it by hand. Signature blocks use a `ts cordis-catalog` fence and include the original source JSDoc immediately before each event or service method. doc-typecheck skips these bare declaration fragments; type names in a signature link to the page that documents them.


## Inherited `ctx` members (cordis core + loader/hmr/timer) [​](#inherited-ctx-members-cordis-core-loader-hmr-timer)


- ctx.on / ctx.once  — Register an event listener (disposable). ( `vendor/cordis/src/events.ts:34` )


- ctx.emit / ctx.parallel / ctx.serial / ctx.bail / ctx.waterfall  — Dispatch an event (sync / awaited / first-bail / short-circuit chain). ( `vendor/cordis/src/events.ts:34` )


- ctx.plugin / ctx.inject  — Load a plugin / declare required services. ( `vendor/cordis/src/registry.ts:164` )


- ctx.effect  — Register a disposable side effect tied to the fiber. ( `vendor/cordis/src/fiber.ts:9` )


- ctx.get / ctx.set / ctx.provide / ctx.accessor / ctx.mixin  — Low-level service-store access and binding. ( `vendor/cordis/src/reflect.ts:7` )


- ctx.extend / ctx.isolate / ctx.intercept  — Derive a child context (scoped services / isolation / interception). ( `vendor/cordis/src/context.ts:42` )


- ctx.root / ctx.scope / ctx.fiber / ctx.registry / ctx.reflect / ctx.events / ctx.logger  — Ambient handles onto the running context graph. ( `vendor/cordis/src/context.ts:16` )


- ctx.timer (+ interval / timeout / throttle / debounce)  — Disposable timer helpers. The  timer  key is provided at runtime; the four supported helpers are mixed onto ctx directly (declared via Pick). ( `vendor/timer/src/index.ts:4` )


- ctx.loader  — The config Loader that booted the app (present under the loader). ( `vendor/loader/src/index.ts:30` )


- ctx.hmr  — The hot-module-reload watcher (present under the hmr plugin). ( `vendor/hmr/src/index.ts:15` )


## Inherited events (cordis core + loader/hmr/timer) [​](#inherited-events-cordis-core-loader-hmr-timer)


- internal/plugin  — A plugin fiber was created. ( `vendor/cordis/src/events.ts:328` )


- internal/status  — A fiber changed lifecycle state. ( `vendor/cordis/src/events.ts:330` )


- internal/service  — Interception hook for a service binding (no core producer). ( `vendor/cordis/src/events.ts:332` )


- internal/update  — Waterfall: a fiber config update is being applied. ( `vendor/cordis/src/events.ts:334` )


- internal/get  — Waterfall: a service is being read from the store. ( `vendor/cordis/src/events.ts:336` )


- internal/set  — Waterfall: a service is being written to the store. ( `vendor/cordis/src/events.ts:338` )


- internal/listener  — A listener was registered. ( `vendor/cordis/src/events.ts:340` )


- internal/dispatch  — An event is being dispatched to listeners. ( `vendor/cordis/src/events.ts:342` )


- hmr/change  — A watched source file changed on disk. ( `vendor/hmr/src/index.ts:20` )


- hmr/reload  — Plugins are being reloaded after a change. ( `vendor/hmr/src/index.ts:21` )


- exit  — The process is exiting on a signal. ( `vendor/loader/src/index.ts:23` )


- loader/config-update  — The loader config tree changed. ( `vendor/loader/src/index.ts:24` )


- loader/entry-init  — A config entry is being initialized. ( `vendor/loader/src/index.ts:25` )


- loader/partial-dispose  — An entry is being partially disposed on reload. ( `vendor/loader/src/index.ts:26` )


- loader/patch-context  — A context is being patched during a reload. ( `vendor/loader/src/index.ts:27` )
