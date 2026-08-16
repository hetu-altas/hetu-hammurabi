/**
 * ConstitutionCoding-Plugin · node 入口（空 apply）
 * 功能插件见 src/command（/cc）、src/gate（硬门禁）、src/status-api（数据通道）。
 * 本入口仅承载包名 entry 激活，使 client 半区（client.js）被 dsh-client-modules 扫描加载。
 */
export const name = "constitution-coding";
export const inject = [];
export function apply() {}
export default { name, inject, apply };
