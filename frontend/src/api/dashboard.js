import client from './client'

export const getStats = async () => {
  const { data } = await client.get('/dashboard/stats')
  return data
}

export const getExpiring = async (days) => {
  const params = days ? { days } : {}
  const { data } = await client.get('/dashboard/expiring', { params })
  return data
}
