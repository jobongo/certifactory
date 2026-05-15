import client from './client'

export const importCA = async (formData) => {
  const { data } = await client.post('/cas/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const importCertificate = async (formData) => {
  const { data } = await client.post('/certificates/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
