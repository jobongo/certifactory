import client from './client'

export const getTokens = async () => {
  const { data } = await client.get('/tokens')
  return data
}

export const createToken = async (name) => {
  const { data } = await client.post('/tokens', { name })
  return data
}

export const revokeToken = async (id) => {
  await client.delete(`/tokens/${id}`)
}
