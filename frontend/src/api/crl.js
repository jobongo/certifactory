import client from './client'

export const generateCRL = async (caId) => {
  const { data } = await client.post(`/cas/${caId}/crl/generate`)
  return data
}

export const downloadCRL = async (caId) => {
  const { data } = await client.get(`/cas/${caId}/crl`, {
    responseType: 'blob',
  })
  return data
}
