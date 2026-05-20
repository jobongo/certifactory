import client from './client'

export const getSettings = async () => {
  const { data } = await client.get('/settings')
  return data
}

export const updateSettings = async (updates) => {
  const { data } = await client.put('/settings', updates)
  return data
}
