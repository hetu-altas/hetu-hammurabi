/**
 * @hetu/dsh-dashboard-panel · node 半区（正式版）
 * 数据通道由 hetu-dashboard-proxy 插件提供（/api/hetu-dashboard 前缀路由转发到
 * 看板服务 8790）；本半区仅承载 client-plugin 包结构。
 */
export const name = "hetu-dashboard";
export const inject = [];
export function apply() {}
export default { name, inject, apply };
