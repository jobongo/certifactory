import client from './client'

export const getCAs = async (page = 1, perPage = 25) => {
  const { data } = await client.get('/cas', { params: { page, per_page: perPage } })
  return data
}

export const getCATree = async () => {
  const { data } = await client.get('/cas/tree')
  return data
}

export const getCA = async (id) => {
  const { data } = await client.get(`/cas/${id}`)
  return data
}

export const createRootCA = async (caData) => {
  const { data } = await client.post('/cas', caData)
  return data
}

export const createIntermediateCA = async (parentId, caData) => {
  const { data } = await client.post(`/cas/${parentId}/intermediate`, caData)
  return data
}

export const updateCA = async (id, caData) => {
  const { data } = await client.put(`/cas/${id}`, caData)
  return data
}

export const getCAChain = async (id) => {
  const { data } = await client.get(`/cas/${id}/chain`)
  return data
}

export const disableCA = async (id) => {
  const { data } = await client.post(`/cas/${id}/disable`)
  return data
}

export const enableCA = async (id) => {
  const { data } = await client.post(`/cas/${id}/enable`)
  return data
}

export const deleteCA = async (id, force = false) => {
  await client.delete(`/cas/${id}`, { params: { force } })
}
