import request from "@/utils/request";

export function listKnowledge(query) {
  return request({
    url: "/ai/knowledge/list",
    method: "get",
    params: query,
  });
}

export function listKnowledgeAll(query) {
  return request({
    url: "/ai/knowledge/all",
    method: "get",
    params: query,
  });
}

export function getKnowledge(documentId) {
  return request({
    url: "/ai/knowledge/" + documentId,
    method: "get",
  });
}

export function uploadKnowledge(data) {
  return request({
    url: "/ai/knowledge/upload",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
}

export function delKnowledge(documentId) {
  return request({
    url: "/ai/knowledge/" + documentId,
    method: "delete",
  });
}

export function reindexKnowledge(documentId, data) {
  return request({
    url: "/ai/knowledge/" + documentId + "/reindex",
    method: "post",
    data,
  });
}
