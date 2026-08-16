
# Service [​](#service)


上下文服务的基类。以插件形式加载的子类会将自身注册为 `ctx.<name>`。


用于在 `ctx` 上公开具名 API 的服务基类。


子类在构造函数中调用 `super(ctx, name)`。服务会立即注册，并随所属 fiber 自动移除。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L11)


### service.name [​](#service-name)




```
/** The service name this instance is registered under. */
public name!: string
```


此实例注册时使用的服务名称。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L30)


## 静态成员 [​](#静态成员)


### Service.init [​](#service-init)




```
/** Symbol key of an instance method run after construction (class plugins). */
static readonly init: unique symbol
```


构造完成后运行的实例方法所使用的符号键（类插件）。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L13)


### Service.check [​](#service-check)




```
/** Symbol key of the availability predicate passed to `ctx.provide()`. */
static readonly check: unique symbol
```


传给 `ctx.provide()` 的可用性谓词所使用的符号键。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L15)


### Service.config [​](#service-config)




```
/** Symbol key of the phantom intercept-config type parameter. */
static readonly config: unique symbol
```


虚设拦截配置类型参数所使用的符号键。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L17)


### Service.invoke [​](#service-invoke)




```
/** Symbol key of the call body making a service callable (e.g. `ctx.logger()`). */
static readonly invoke: unique symbol
```


使服务可被调用的调用体所使用的符号键（例如 `ctx.logger()`）。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L19)


### Service.extend [​](#service-extend)




```
/** Symbol key of the helper deriving an extended service instance. */
static readonly extend: unique symbol
```


用于派生扩展服务实例的辅助方法所使用的符号键。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L21)


### Service.tracker [​](#service-tracker)




```
/** Symbol key of the tracker metadata used for context tracing. */
static readonly tracker: unique symbol
```


上下文追踪所用跟踪器元数据的符号键。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L23)


### Service.resolveConfig [​](#service-resolveconfig)




```
/** Symbol key of the intercept-config resolution helper below. */
static readonly resolveConfig: unique symbol
```


下述拦截配置解析辅助方法所使用的符号键。


[源码](https://github.com/deepseek-ai/deepseek-harness/blob/master/vendor/cordis/src/service.ts#L25)
