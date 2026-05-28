import client from './client'

export const getTLSInfo = async () => {
  const { data } = await client.get('/tls')
  return data
}

export const uploadTLSCert = async (certData) => {
  const { data } = await client.post('/tls/upload', certData)
  return data
}

export const issueTLSCert = async (issueData) => {
  const { data } = await client.post('/tls/issue', issueData)
  return data
}
