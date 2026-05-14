import client from './client'

export const getAuditLogs = async (params = {}) => {
  const { data } = await client.get('/audit/logs', { params })
  return data
}

export const exportAuditLogs = async (params = {}) => {
  const { data } = await client.get('/audit/logs/export', {
    params,
    responseType: 'blob',
  })
  return data
}
