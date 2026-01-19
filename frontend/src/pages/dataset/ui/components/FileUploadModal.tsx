import { useState, useRef, useEffect } from "react";
import * as S from "./fileUploadModal.styles";
import { apiClient } from "@/shared/api";

interface FileUploadModalProps {
  projectId: number;
  projectName: string;
  onClose: () => void;
  onFileUploaded?: () => void;
}

interface UploadedFile {
  id: number;
  name: string;
  size: string;
  createdAt: string;
  projectId?: number;
  filePath?: string;
  isPending?: boolean;
}

export const FileUploadModal = ({ projectId, projectName, onClose, onFileUploaded }: FileUploadModalProps) => {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [assigningFileId, setAssigningFileId] = useState<number | null>(null);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        setLoadingFiles(true);
        // 해당 프로젝트의 모든 파일 가져오기 (pending + applied)
        const allFiles = (await apiClient.getDataFiles(projectId, false)) as UploadedFile[];
        // 디버깅: 파일 상태 확인
        console.log("Fetched files:", allFiles.map(f => ({ name: f.name, isPending: f.isPending, filePath: f.filePath })));
        setUploadedFiles(allFiles);
      } catch (err) {
        console.error("Failed to fetch files:", err);
      } finally {
        setLoadingFiles(false);
      }
    };
    fetchFiles();
  }, [projectId]);

  const refreshFiles = async () => {
    try {
      setLoadingFiles(true);
      // 해당 프로젝트의 모든 파일 가져오기 (pending + applied)
      const allFiles = (await apiClient.getDataFiles(projectId, false)) as UploadedFile[];
      setUploadedFiles(allFiles);
    } catch (err) {
      console.error("Failed to fetch files:", err);
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    try {
      setUploading(true);
      setUploadError(null);
      setUploadSuccess(false);
      // 해당 프로젝트에 임시 저장 (pending 상태)
      // const result = await apiClient.uploadFile(file, projectId) as { file?: UploadedFile; message?: string };
      // console.log("Upload result:", result);
      
      // API 응답에서 파일 정보를 가져와서 업로드된 파일 리스트에 추가
      // if (result.file) {
      //   const uploadedFile: UploadedFile = {
      //     ...result.file,
      //     isPending: true, // pending 상태로 명시적으로 설정
      //   };
      //   setUploadedFiles((prev) => [...prev, uploadedFile]);
      // }


      
      setUploadSuccess(true);
      setTimeout(() => setUploadSuccess(false), 3000);

      // 파일 목록 새로고침하지 않음 - API 응답의 파일 정보를 직접 사용
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "파일 업로드에 실패했습니다.");
      console.error("Failed to upload file:", err);
    } finally {
      setUploading(false);
    }
  };


  return (
    <S.Modal onClick={(e) => e.target === e.currentTarget && onClose()}>
      <S.ModalContent>
        <S.ModalHeader>
          <S.ModalTitle>
            파일 업로드 - {projectName}
          </S.ModalTitle>
        </S.ModalHeader>

        <S.ModalBody>
          <S.UploadArea
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={async (e) => {
              e.preventDefault();
              const files = Array.from(e.dataTransfer.files);
              if (files.length > 0) {
                await handleFileUpload(files[0]);
              }
            }}
          >
            <S.UploadIcon>📁</S.UploadIcon>
            <S.UploadTitle>파일을 드래그하거나 클릭하여 업로드</S.UploadTitle>
            <S.UploadSubtitle>CSV, Excel, TSV, JSON 형식 지원 (최대 500MB)</S.UploadSubtitle>
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: "none" }}
              accept=".csv,.xlsx,.tsv,.json"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) {
                  // await handleFileUpload(file);
                  const newFile: UploadedFile = { id: uploadedFiles.length + 1, name: file.name, size: file.size.toString(), createdAt: new Date().toISOString(), isPending: true };
                  setUploadedFiles([...uploadedFiles, newFile]);
                }
              }}
            />
          </S.UploadArea>
          {uploadError && <div style={{ color: "red", marginTop: "1rem" }}>에러: {uploadError}</div>}
          {uploadSuccess && <div style={{ color: "green", marginTop: "1rem" }}>파일이 성공적으로 업로드되었습니다!</div>}
          {uploading && <div style={{ marginTop: "1rem" }}>업로드 중...</div>}

          <div style={{ marginTop: "2rem" }}>
            {(() => {
              // isPending이 없으면 filePath로 판단
              const pendingFiles = uploadedFiles.filter((f) => {
                if (f.isPending !== undefined) {
                  return f.isPending;
                }
                return f.filePath && f.filePath.includes("pending");
              });
              const appliedFiles = uploadedFiles.filter((f) => {
                if (f.isPending !== undefined) {
                  return !f.isPending;
                }
                return !f.filePath || !f.filePath.includes("pending");
              });
              
              return (
                <>
                  {/* 프로젝트에 적용 대기 중인 파일 */}
                  <div style={{ marginBottom: "2rem" }}>
                    <h4 style={{ marginBottom: "1rem", fontSize: "1rem", fontWeight: "bold" }}>
                      업로드한 파일 ({pendingFiles.length})
                    </h4>
                    {loadingFiles ? (
                      <div style={{ color: "#666" }}>파일 목록 로딩 중...</div>
                    ) : pendingFiles.length === 0 ? (
                      <div style={{ color: "#666", padding: "1rem", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
                        업로드한 파일이 없습니다.
                      </div>
                    ) : (
                      <div style={{ border: "1px solid #e0e0e0", borderRadius: "4px", overflow: "hidden" }}>
                        {pendingFiles.map((file, index) => {
                          const isAssigning = assigningFileId === file.id;
                          
                          return (
                            <div
                              key={file.id || index}
                              style={{
                                padding: "0.75rem 1rem",
                                borderBottom: index < pendingFiles.length - 1 ? "1px solid #e0e0e0" : "none",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                              }}
                            >
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: "500" }}>{file.name}</div>
                                <div style={{ fontSize: "0.875rem", color: "#666", marginTop: "0.25rem" }}>
                                  {file.size} • {file.createdAt || "날짜 미상"}
                                </div>
                              </div>
                              <S.Button
                                $variant="primary"
                                onClick={async () => {
                                  if (!projectId) {
                                    setUploadError("프로젝트를 선택해주세요.");
                                    return;
                                  }

                                  try {
                                    setUploading(true);
                                    setUploadError(null);
                                    setUploadSuccess(false);
                                    
                                    // 파일 객체를 가져오기 위해 fetch 사용
                                    const fileResponse = await fetch(file.filePath || `/api/data/${file.id}/download`);
                                    const blob = await fileResponse.blob();
                                    const fileObj = new File([blob], file.name, { type: blob.type });
                                    
                                    await apiClient.uploadFile(fileObj, projectId);
                                    setUploadSuccess(true);
                                    setTimeout(() => setUploadSuccess(false), 3000);

                                    // 파일 목록 새로고침
                                    await refreshFiles();

                                    // 파일 업로드 성공 시 프로젝트 목록 갱신
                                    if (onFileUploaded) {
                                      onFileUploaded();
                                    }
                                  } catch (err) {
                                    setUploadError(err instanceof Error ? err.message : "파일 업로드에 실패했습니다.");
                                    console.error("Failed to upload file:", err);
                                  } finally {
                                    setUploading(false);
                                  }
                                }}
                                disabled={isAssigning || uploading}
                                style={{ marginLeft: "1rem", padding: "0.5rem 1rem", fontSize: "0.875rem" }}
                              >
                                {isAssigning ? "적용 중..." : "프로젝트에 적용"}
                              </S.Button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* 프로젝트에 적용 완료된 파일 */}
                  <div>
                    <h4 style={{ marginBottom: "1rem", fontSize: "1rem", fontWeight: "bold" }}>
                      프로젝트에 적용된 파일 ({appliedFiles.length})
                    </h4>
                    {appliedFiles.length === 0 ? (
                      <div style={{ color: "#666", padding: "1rem", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
                        적용 완료된 파일이 없습니다.
                      </div>
                    ) : (
                      <div style={{ border: "1px solid #e0e0e0", borderRadius: "4px", overflow: "hidden" }}>
                        {appliedFiles.map((file, index) => (
                          <div
                            key={file.id || index}
                            style={{
                              padding: "0.75rem 1rem",
                              borderBottom: index < appliedFiles.length - 1 ? "1px solid #e0e0e0" : "none",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              backgroundColor: "#f0f9ff",
                            }}
                          >
                            <div style={{ flex: 1 }}>
                              <div style={{ fontWeight: "500", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                {file.name}
                                <span style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: "600" }}>
                                  (적용 완료)
                                </span>
                              </div>
                              <div style={{ fontSize: "0.875rem", color: "#666", marginTop: "0.25rem" }}>
                                {file.size} • {file.createdAt || "날짜 미상"}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              );
            })()}
          </div>
        </S.ModalBody>

        <S.ModalFooter>
          <S.Button $variant="secondary" onClick={onClose} disabled={uploading}>
            닫기
          </S.Button>
        </S.ModalFooter>
      </S.ModalContent>
    </S.Modal>
  );
};
