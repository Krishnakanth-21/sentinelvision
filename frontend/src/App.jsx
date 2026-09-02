import { useCallback, useEffect, useState } from "react";
import "./App.css";


// ===========================================================================
// API configuration
// ===========================================================================

// SentinelVision AWS serverless backend.
//
// Production:
// React / Vercel
//      ↓
// API Gateway
//      ↓
// Lambda
//      ↓
// Presigned URL
//      ↓
// Amazon S3
//
// VITE_API_BASE_URL can override the default endpoint when required.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "https://h65jn9tkr5.execute-api.ap-southeast-2.amazonaws.com";


// Browser-local dataset history.
//
// This is temporary application state.
// A persistent AWS metadata store will be connected later.
const DATASET_STORAGE_KEY =
  "sentinelvision_dataset_history";


// Maximum client-side upload sizes.
const MAX_IMAGE_SIZE_BYTES =
  20 * 1024 * 1024;

const MAX_VIDEO_SIZE_BYTES =
  200 * 1024 * 1024;


// ===========================================================================
// Utility functions
// ===========================================================================

/**
 * Convert a byte value into a human-readable file size.
 *
 * @param {number} bytes File size in bytes.
 * @returns {string} Human-readable file size.
 */
function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) {
    return "N/A";
  }

  if (bytes === 0) {
    return "0 Bytes";
  }

  const units = [
    "Bytes",
    "KB",
    "MB",
    "GB",
  ];

  const unitIndex = Math.min(
    Math.floor(
      Math.log(bytes) /
        Math.log(1024)
    ),
    units.length - 1
  );

  const value =
    bytes /
    Math.pow(
      1024,
      unitIndex
    );

  return `${value.toFixed(2)} ${units[unitIndex]}`;
}


/**
 * Return the locally stored SentinelVision datasets.
 *
 * @returns {Array} Dataset history.
 */
function readDatasetHistory() {
  try {
    const storedValue =
      window.localStorage.getItem(
        DATASET_STORAGE_KEY
      );

    if (!storedValue) {
      return [];
    }

    const parsedValue =
      JSON.parse(storedValue);

    return Array.isArray(parsedValue)
      ? parsedValue
      : [];
  } catch (error) {
    console.error(
      "[SentinelVision] Failed to read local dataset history:",
      error
    );

    return [];
  }
}


/**
 * Save SentinelVision dataset history locally.
 *
 * @param {Array} datasets Dataset history.
 */
function saveDatasetHistory(
  datasets
) {
  try {
    window.localStorage.setItem(
      DATASET_STORAGE_KEY,
      JSON.stringify(datasets)
    );
  } catch (error) {
    console.error(
      "[SentinelVision] Failed to save local dataset history:",
      error
    );
  }
}


/**
 * Validate a file before requesting an AWS presigned URL.
 *
 * @param {"image"|"video"} mediaType Media type.
 * @param {File} file Browser File object.
 */
function validateSelectedFile(
  mediaType,
  file
) {
  const extension =
    file.name
      .split(".")
      .pop()
      ?.toLowerCase();

  if (mediaType === "image") {
    const allowedExtensions = [
      "jpg",
      "jpeg",
      "png",
      "avif",
    ];

    if (
      !extension ||
      !allowedExtensions.includes(
        extension
      )
    ) {
      throw new Error(
        "Supported image formats are JPG, JPEG, PNG and AVIF."
      );
    }

    if (
      file.size >
      MAX_IMAGE_SIZE_BYTES
    ) {
      throw new Error(
        "The image exceeds the 20 MB upload limit."
      );
    }

    return;
  }

  if (
    extension !== "mp4"
  ) {
    throw new Error(
      "Only MP4 video files are currently supported."
    );
  }

  if (
    file.size >
    MAX_VIDEO_SIZE_BYTES
  ) {
    throw new Error(
      "The video exceeds the 200 MB upload limit."
    );
  }
}


// ===========================================================================
// Reusable components
// ===========================================================================

/**
 * Navigation bar displayed at the top of the application.
 */
function Navigation() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <a
          href="#home"
          className="brand"
          aria-label="SentinelVision home"
        >
          <div className="brand-icon">
            SV
          </div>

          <div>
            <div className="brand-name">
              SentinelVision
            </div>

            <div className="brand-subtitle">
              Visual Data Intelligence
            </div>
          </div>
        </a>

        <nav className="nav-links">
          <a href="#analyse">
            Upload
          </a>

          <a href="#datasets">
            Datasets
          </a>

          <a href="#guide">
            Guide
          </a>

          <a href="#system">
            System
          </a>
        </nav>
      </div>
    </header>
  );
}


/**
 * Hero section explaining the platform.
 *
 * @param {string} apiStatus Current AWS API status.
 */
function Hero({
  apiStatus,
}) {
  const online =
    apiStatus === "healthy";

  return (
    <section
      id="home"
      className="hero-section"
    >
      <div className="hero-content">
        <div className="eyebrow">
          Serverless image & video data ingestion
        </div>

        <h1>
          Understand your visual data
          <span>
            {" "}
            before your model does.
          </span>
        </h1>

        <p className="hero-description">
          SentinelVision securely ingests
          images and videos into an
          ML-oriented AWS data pipeline
          using serverless APIs and
          direct Amazon S3 uploads.
        </p>

        <div className="hero-actions">
          <a
            href="#analyse"
            className="primary-button"
          >
            Upload your data
          </a>

          <a
            href="#guide"
            className="secondary-button"
          >
            How it works
          </a>
        </div>

        <div className="hero-status">
          <span
            className={
              online
                ? "status-dot status-dot-online"
                : "status-dot status-dot-offline"
            }
          />

          AWS API status:

          <strong>
            {apiStatus}
          </strong>
        </div>
      </div>

      <div className="hero-visual">
        <div className="pipeline-card">
          <div className="pipeline-title">
            SentinelVision Pipeline
          </div>

          <div className="pipeline-step">
            <span className="pipeline-number">
              01
            </span>

            <div>
              <strong>
                Request
              </strong>

              <small>
                Presigned upload URL
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              02
            </span>

            <div>
              <strong>
                Upload
              </strong>

              <small>
                Browser directly to S3
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              03
            </span>

            <div>
              <strong>
                Store
              </strong>

              <small>
                Dataset-specific S3 path
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              04
            </span>

            <div>
              <strong>
                Process
              </strong>

              <small>
                Ready for ML analysis
              </small>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}


/**
 * General platform statistics shown below the hero.
 */
function FeatureStats() {
  return (
    <section className="feature-stats">
      <div className="stat">
        <strong>
          Images
        </strong>

        <span>
          JPG · JPEG · PNG · AVIF
        </span>
      </div>

      <div className="stat">
        <strong>
          Videos
        </strong>

        <span>
          MP4 ingestion
        </span>
      </div>

      <div className="stat">
        <strong>
          Architecture
        </strong>

        <span>
          Event-ready serverless
        </span>
      </div>

      <div className="stat">
        <strong>
          Storage
        </strong>

        <span>
          Amazon S3
        </span>
      </div>
    </section>
  );
}


/**
 * File upload card.
 */
function UploadCard({
  mediaType,
  title,
  description,
  accept,
  file,
  onFileChange,
  onUpload,
  uploading,
}) {
  const inputId =
    `${mediaType}-file-input`;

  return (
    <div className="upload-card">
      <div className="upload-card-header">
        <div
          className={`media-icon ${mediaType}-icon`}
        >
          {mediaType === "image"
            ? "IMG"
            : "VID"}
        </div>

        <div>
          <h3>
            {title}
          </h3>

          <p>
            {description}
          </p>
        </div>
      </div>

      <label
        className="file-drop-zone"
        htmlFor={inputId}
      >
        <span className="upload-symbol">
          ↑
        </span>

        <strong>
          Choose a {mediaType}
        </strong>

        <span>
          Click to browse your device
        </span>

        <input
          id={inputId}
          type="file"
          accept={accept}
          onChange={onFileChange}
        />
      </label>

      {file && (
        <div className="selected-file">
          <div>
            <strong>
              {file.name}
            </strong>

            <span>
              {formatBytes(
                file.size
              )}
            </span>
          </div>

          <span className="selected-badge">
            Ready
          </span>
        </div>
      )}

      <button
        className="upload-button"
        type="button"
        onClick={onUpload}
        disabled={
          !file ||
          uploading
        }
      >
        {uploading
          ? "Uploading..."
          : `Upload ${mediaType}`
        }
      </button>

      <p className="upload-limit">
        {mediaType === "image"
          ? "Maximum file size: 20 MB"
          : "Maximum file size: 200 MB"
        }
      </p>
    </div>
  );
}


/**
 * Upload result returned after the direct-to-S3 workflow succeeds.
 */
function UploadResult({
  response,
}) {
  if (!response) {
    return null;
  }

  return (
    <section className="result-panel">
      <div className="section-heading">
        <div>
          <span className="section-label">
            Upload complete
          </span>

          <h2>
            File stored successfully
          </h2>
        </div>

        <span className="success-pill">
          Success
        </span>
      </div>

      <div className="result-message">
        <strong>
          {response.original_filename}
        </strong>

        <span>
          Your file was uploaded directly
          to Amazon S3 using a temporary
          presigned URL.
        </span>
      </div>

      <div className="dataset-id-box">
        <div>
          <span>
            Dataset ID
          </span>

          <code>
            {response.dataset_id}
          </code>
        </div>

        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(
              response.dataset_id
            );

            console.info(
              "[SentinelVision] Dataset ID copied:",
              response.dataset_id
            );
          }}
        >
          Copy ID
        </button>
      </div>

      <h3 className="subsection-title">
        Upload information
      </h3>

      <div className="metadata-table">
        <div className="metadata-row">
          <span>
            Media type
          </span>

          <strong>
            {response.media_type}
          </strong>
        </div>

        <div className="metadata-row">
          <span>
            File size
          </span>

          <strong>
            {formatBytes(
              response.file_size_bytes
            )}
          </strong>
        </div>

        <div className="metadata-row">
          <span>
            Storage status
          </span>

          <strong>
            Stored in Amazon S3
          </strong>
        </div>

        <div className="metadata-row">
          <span>
            Upload architecture
          </span>

          <strong>
            Direct-to-S3
          </strong>
        </div>
      </div>

      <div className="storage-information">
        <strong>
          S3 object key
        </strong>

        <code>
          {response.s3_key}
        </code>
      </div>
    </section>
  );
}


/**
 * Dataset information stored by the browser.
 */
function DatasetDetails({
  dataset,
}) {
  if (!dataset) {
    return null;
  }

  return (
    <div className="dataset-details">
      <div className="dataset-details-header">
        <span>
          Dataset
        </span>

        <code>
          {dataset.dataset_id}
        </code>
      </div>

      <div className="dataset-count-grid">
        <div>
          <strong>
            {dataset.images?.length ??
              0}
          </strong>

          <span>
            Images
          </span>
        </div>

        <div>
          <strong>
            {dataset.videos?.length ??
              0}
          </strong>

          <span>
            Videos
          </span>
        </div>
      </div>

      {dataset.images?.map(
        (
          image,
          index
        ) => (
          <div
            className="dataset-media-item"
            key={`image-${index}`}
          >
            <div>
              <span className="dataset-type">
                IMAGE
              </span>

              <strong>
                {
                  image.original_filename
                }
              </strong>
            </div>

            <span>
              {formatBytes(
                image.file_size_bytes
              )}
            </span>
          </div>
        )
      )}

      {dataset.videos?.map(
        (
          video,
          index
        ) => (
          <div
            className="dataset-media-item"
            key={`video-${index}`}
          >
            <div>
              <span className="dataset-type">
                VIDEO
              </span>

              <strong>
                {
                  video.original_filename
                }
              </strong>
            </div>

            <span>
              {formatBytes(
                video.file_size_bytes
              )}
            </span>
          </div>
        )
      )}
    </div>
  );
}


// ===========================================================================
// Main application
// ===========================================================================

function App() {
  // -------------------------------------------------------------------------
  // System state
  // -------------------------------------------------------------------------

  const [
    apiStatus,
    setApiStatus,
  ] = useState(
    "Checking..."
  );

  const [
    systemError,
    setSystemError,
  ] = useState("");


  // -------------------------------------------------------------------------
  // Upload state
  // -------------------------------------------------------------------------

  const [
    imageFile,
    setImageFile,
  ] = useState(null);

  const [
    videoFile,
    setVideoFile,
  ] = useState(null);

  const [
    uploadingType,
    setUploadingType,
  ] = useState("");

  const [
    uploadError,
    setUploadError,
  ] = useState("");

  const [
    uploadResult,
    setUploadResult,
  ] = useState(null);


  // -------------------------------------------------------------------------
  // Dataset state
  // -------------------------------------------------------------------------

  const [
    datasets,
    setDatasets,
  ] = useState([]);

  const [
    datasetQuery,
    setDatasetQuery,
  ] = useState("");

  const [
    datasetDetails,
    setDatasetDetails,
  ] = useState(null);

  const [
    datasetError,
    setDatasetError,
  ] = useState("");

  const [
    datasetLoading,
    setDatasetLoading,
  ] = useState(false);


  // -------------------------------------------------------------------------
  // AWS API connectivity check
  // -------------------------------------------------------------------------

  const checkApiHealth =
    useCallback(
      async () => {
        console.info(
          "[SentinelVision] Checking AWS API connectivity..."
        );

        setApiStatus(
          "Checking..."
        );

        try {
          const response =
            await fetch(
              `${API_BASE_URL}/upload-url`,
              {
                method:
                  "OPTIONS",
              }
            );

          if (
            !response.ok
          ) {
            throw new Error(
              `API Gateway returned HTTP ${response.status}`
            );
          }

          console.info(
            "[SentinelVision] AWS API Gateway is reachable."
          );

          setApiStatus(
            "healthy"
          );

          setSystemError(
            ""
          );
        } catch (error) {
          console.error(
            "[SentinelVision] AWS API connectivity check failed:",
            error
          );

          setApiStatus(
            "Unavailable"
          );

          setSystemError(
            "The SentinelVision AWS upload API cannot currently be reached."
          );
        }
      },
      []
    );


  // -------------------------------------------------------------------------
  // Dataset history
  // -------------------------------------------------------------------------

  const loadDatasets =
    useCallback(() => {
      const history =
        readDatasetHistory();

      console.info(
        "[SentinelVision] Local dataset history loaded:",
        history.length
      );

      setDatasets(
        history
      );
    }, []);


  // -------------------------------------------------------------------------
  // Initial application loading
  // -------------------------------------------------------------------------

  useEffect(() => {
    console.info(
      "[SentinelVision] React application started."
    );

    console.info(
      "[SentinelVision] AWS API:",
      API_BASE_URL
    );

    checkApiHealth();
    loadDatasets();
  }, [
    checkApiHealth,
    loadDatasets,
  ]);


  // -------------------------------------------------------------------------
  // File selection
  // -------------------------------------------------------------------------

  function handleImageSelection(
    event
  ) {
    const selectedFile =
      event.target
        .files?.[0];

    if (!selectedFile) {
      return;
    }

    console.info(
      "[SentinelVision] Image selected:",
      selectedFile.name,
      selectedFile.size,
      "bytes"
    );

    setImageFile(
      selectedFile
    );

    setUploadError(
      ""
    );
  }


  function handleVideoSelection(
    event
  ) {
    const selectedFile =
      event.target
        .files?.[0];

    if (!selectedFile) {
      return;
    }

    console.info(
      "[SentinelVision] Video selected:",
      selectedFile.name,
      selectedFile.size,
      "bytes"
    );

    setVideoFile(
      selectedFile
    );

    setUploadError(
      ""
    );
  }


  // -------------------------------------------------------------------------
  // Serverless upload workflow
  // -------------------------------------------------------------------------

  async function uploadMedia(
    mediaType,
    file
  ) {
    if (!file) {
      setUploadError(
        `Please choose a ${mediaType} first.`
      );

      return;
    }

    console.info(
      `[SentinelVision] Starting serverless ${mediaType} upload:`,
      file.name
    );

    setUploadingType(
      mediaType
    );

    setUploadError(
      ""
    );

    setUploadResult(
      null
    );

    try {
      // ---------------------------------------------------------------------
      // Step 1: Validate locally before calling AWS.
      // ---------------------------------------------------------------------

      validateSelectedFile(
        mediaType,
        file
      );


      // ---------------------------------------------------------------------
      // Step 2: Ask API Gateway/Lambda for a temporary S3 upload URL.
      // ---------------------------------------------------------------------

      console.info(
        "[SentinelVision] Requesting presigned S3 URL..."
      );

      const presignedResponse =
        await fetch(
          `${API_BASE_URL}/upload-url`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                filename:
                  file.name,

                media_type:
                  mediaType,
              }),
          }
        );


      const presignedData =
        await presignedResponse.json();


      if (
        !presignedResponse.ok
      ) {
        throw new Error(
          presignedData.error ||
          `Unable to create upload URL. HTTP ${presignedResponse.status}`
        );
      }


      if (
        !presignedData.upload_url ||
        !presignedData.dataset_id ||
        !presignedData.s3_key
      ) {
        throw new Error(
          "The AWS upload API returned an incomplete response."
        );
      }


      console.info(
        "[SentinelVision] Presigned URL created:",
        presignedData.dataset_id
      );


      // ---------------------------------------------------------------------
      // Step 3: Upload the actual file directly from the browser to Amazon S3.
      //
      // The file does NOT pass through Lambda or API Gateway.
      // ---------------------------------------------------------------------

      console.info(
        "[SentinelVision] Uploading file directly to Amazon S3..."
      );


      const s3Response =
        await fetch(
          presignedData.upload_url,
          {
            method:
              "PUT",

            body:
              file,
          }
        );


      if (
        !s3Response.ok
      ) {
        throw new Error(
          `Amazon S3 upload failed with HTTP ${s3Response.status}.`
        );
      }


      console.info(
        "[SentinelVision] Direct S3 upload completed successfully:",
        presignedData.s3_key
      );


      // ---------------------------------------------------------------------
      // Step 4: Build a browser-side dataset record.
      //
      // Persistent metadata storage will move to AWS in a later stage.
      // ---------------------------------------------------------------------

      const mediaRecord = {
        original_filename:
          file.name,

        file_size_bytes:
          file.size,

        s3_key:
          presignedData.s3_key,

        uploaded_at:
          new Date().toISOString(),
      };


      const dataset = {
        dataset_id:
          presignedData.dataset_id,

        created_at:
          new Date().toISOString(),

        images:
          mediaType === "image"
            ? [mediaRecord]
            : [],

        videos:
          mediaType === "video"
            ? [mediaRecord]
            : [],
      };


      const currentHistory =
        readDatasetHistory();


      const updatedHistory = [
        dataset,
        ...currentHistory,
      ].slice(
        0,
        50
      );


      saveDatasetHistory(
        updatedHistory
      );


      setDatasets(
        updatedHistory
      );


      setUploadResult({
        status:
          "success",

        dataset_id:
          presignedData.dataset_id,

        original_filename:
          file.name,

        file_size_bytes:
          file.size,

        media_type:
          mediaType,

        s3_key:
          presignedData.s3_key,
      });


      setApiStatus(
        "healthy"
      );


      // Automatically bring the result into view.
      window.setTimeout(
        () => {
          document
            .getElementById(
              "analysis-result"
            )
            ?.scrollIntoView({
              behavior:
                "smooth",

              block:
                "start",
            });
        },
        100
      );

    } catch (error) {
      console.error(
        `[SentinelVision] ${mediaType} upload failed:`,
        error
      );

      setUploadError(
        error.message ||
        "The file could not be uploaded."
      );
    } finally {
      setUploadingType(
        ""
      );

      console.info(
        `[SentinelVision] ${mediaType} upload workflow finished.`
      );
    }
  }


  // -------------------------------------------------------------------------
  // Dataset lookup
  // -------------------------------------------------------------------------

  async function lookupDataset(
    event
  ) {
    event.preventDefault();

    const datasetId =
      datasetQuery.trim();

    if (!datasetId) {
      setDatasetError(
        "Enter a dataset ID first."
      );

      return;
    }

    console.info(
      "[SentinelVision] Looking up local dataset:",
      datasetId
    );

    setDatasetLoading(
      true
    );

    setDatasetError(
      ""
    );

    setDatasetDetails(
      null
    );

    try {
      const history =
        readDatasetHistory();

      const match =
        history.find(
          (dataset) =>
            dataset.dataset_id ===
            datasetId
        );

      if (!match) {
        throw new Error(
          "Dataset was not found in this browser's local history."
        );
      }

      setDatasetDetails(
        match
      );

      console.info(
        "[SentinelVision] Dataset lookup successful:",
        datasetId
      );
    } catch (error) {
      console.error(
        "[SentinelVision] Dataset lookup failed:",
        error
      );

      setDatasetError(
        error.message
      );
    } finally {
      setDatasetLoading(
        false
      );
    }
  }


  // -------------------------------------------------------------------------
  // Application UI
  // -------------------------------------------------------------------------

  return (
    <>
      <Navigation />

      <main>
        <Hero
          apiStatus={
            apiStatus
          }
        />

        <FeatureStats />


        {/* --------------------------------------------------------------- */}
        {/* Upload                                                         */}
        {/* --------------------------------------------------------------- */}

        <section
          id="analyse"
          className="page-section"
        >
          <div className="section-heading centered-heading">
            <div>
              <span className="section-label">
                Start here
              </span>

              <h2>
                Upload visual data
              </h2>

              <p>
                Choose an image or
                video. SentinelVision
                requests temporary
                upload permission from
                AWS and sends the file
                directly from your
                browser to Amazon S3.
              </p>
            </div>
          </div>

          <div className="upload-grid">
            <UploadCard
              mediaType="image"
              title="Upload an image"
              description="Securely ingest JPG, JPEG, PNG or AVIF imagery into the SentinelVision AWS data pipeline."
              accept=".jpg,.jpeg,.png,.avif"
              file={
                imageFile
              }
              onFileChange={
                handleImageSelection
              }
              onUpload={() =>
                uploadMedia(
                  "image",
                  imageFile
                )
              }
              uploading={
                uploadingType ===
                "image"
              }
            />

            <UploadCard
              mediaType="video"
              title="Upload a video"
              description="Securely ingest MP4 video directly into dataset-specific Amazon S3 storage."
              accept=".mp4"
              file={
                videoFile
              }
              onFileChange={
                handleVideoSelection
              }
              onUpload={() =>
                uploadMedia(
                  "video",
                  videoFile
                )
              }
              uploading={
                uploadingType ===
                "video"
              }
            />
          </div>

          {uploadError && (
            <div className="error-banner">
              <strong>
                Upload failed
              </strong>

              <span>
                {
                  uploadError
                }
              </span>
            </div>
          )}

          <div id="analysis-result">
            <UploadResult
              response={
                uploadResult
              }
            />
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* Dataset explorer                                               */}
        {/* --------------------------------------------------------------- */}

        <section
          id="datasets"
          className="page-section alternate-section"
        >
          <div className="section-heading">
            <div>
              <span className="section-label">
                Dataset explorer
              </span>

              <h2>
                Find recent uploads
              </h2>

              <p>
                Every upload receives a
                unique dataset ID.
                Dataset history is
                currently stored in this
                browser while the
                persistent AWS metadata
                layer is being built.
              </p>
            </div>
          </div>

          <div className="dataset-layout">
            <div className="dataset-search-card">
              <h3>
                Search by dataset ID
              </h3>

              <p>
                Paste an ID returned
                after an upload.
              </p>

              <form
                onSubmit={
                  lookupDataset
                }
                className="dataset-search-form"
              >
                <input
                  type="text"
                  value={
                    datasetQuery
                  }
                  onChange={(
                    event
                  ) =>
                    setDatasetQuery(
                      event
                        .target
                        .value
                    )
                  }
                  placeholder="e.g. 9787d7c6-90d2-43e1..."
                />

                <button
                  type="submit"
                  disabled={
                    datasetLoading
                  }
                >
                  {datasetLoading
                    ? "Searching..."
                    : "Find dataset"
                  }
                </button>
              </form>

              {datasetError && (
                <p className="inline-error">
                  {
                    datasetError
                  }
                </p>
              )}

              <DatasetDetails
                dataset={
                  datasetDetails
                }
              />
            </div>

            <div className="recent-datasets-card">
              <div className="card-title-row">
                <div>
                  <h3>
                    Recent datasets
                  </h3>

                  <p>
                    This browser
                  </p>
                </div>

                <span className="count-badge">
                  {
                    datasets.length
                  }
                </span>
              </div>

              {datasets.length ===
              0 ? (
                <div className="empty-state">
                  <strong>
                    No datasets yet
                  </strong>

                  <span>
                    Upload an image or
                    video to create
                    your first dataset.
                  </span>
                </div>
              ) : (
                <div className="recent-dataset-list">
                  {datasets.map(
                    (
                      dataset
                    ) => (
                      <button
                        type="button"
                        className="recent-dataset"
                        key={
                          dataset.dataset_id
                        }
                        onClick={() => {
                          setDatasetQuery(
                            dataset.dataset_id
                          );

                          setDatasetDetails(
                            dataset
                          );

                          setDatasetError(
                            ""
                          );
                        }}
                      >
                        <code>
                          {
                            dataset.dataset_id
                          }
                        </code>

                        <span>
                          {dataset
                            .images
                            ?.length ??
                            0}{" "}
                          image
                          {(dataset
                            .images
                            ?.length ??
                            0) !==
                          1
                            ? "s"
                            : ""}
                          {" · "}
                          {dataset
                            .videos
                            ?.length ??
                            0}{" "}
                          video
                          {(dataset
                            .videos
                            ?.length ??
                            0) !==
                          1
                            ? "s"
                            : ""}
                        </span>
                      </button>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* User guidance                                                  */}
        {/* --------------------------------------------------------------- */}

        <section
          id="guide"
          className="page-section"
        >
          <div className="section-heading centered-heading">
            <div>
              <span className="section-label">
                User guide
              </span>

              <h2>
                How SentinelVision works
              </h2>

              <p>
                SentinelVision uses a
                serverless ingestion
                architecture so large
                media files do not need
                to travel through an
                application server.
              </p>
            </div>
          </div>

          <div className="guide-grid">
            <article className="guide-card">
              <span className="guide-number">
                01
              </span>

              <h3>
                Choose your media
              </h3>

              <p>
                Select a supported
                image or MP4 video
                from your device.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                02
              </span>

              <h3>
                Request permission
              </h3>

              <p>
                API Gateway invokes an
                AWS Lambda function
                that generates a
                short-lived presigned
                S3 upload URL.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                03
              </span>

              <h3>
                Direct S3 upload
              </h3>

              <p>
                Your browser uploads
                the media directly to
                a dataset-specific
                Amazon S3 location.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                04
              </span>

              <h3>
                Ready for processing
              </h3>

              <p>
                The stored object can
                trigger downstream
                metadata extraction,
                quality validation
                and ML-readiness
                processing.
              </p>
            </article>
          </div>


          <div className="metric-guide">
            <div className="metric-guide-heading">
              <span className="section-label">
                Why this architecture?
              </span>

              <h2>
                Designed for visual
                data engineering
              </h2>
            </div>

            <div className="metric-list">
              <div className="metric-item">
                <strong>
                  Presigned URLs
                </strong>

                <p>
                  Provide temporary
                  permission to upload
                  one specific S3
                  object without
                  exposing AWS
                  credentials to the
                  browser.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Direct-to-S3
                </strong>

                <p>
                  Large media bypasses
                  API Gateway and
                  Lambda payload
                  limits by travelling
                  directly from the
                  browser to object
                  storage.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Dataset IDs
                </strong>

                <p>
                  Every upload receives
                  a UUID so raw media
                  and future processing
                  results can be
                  grouped reliably.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Least privilege
                </strong>

                <p>
                  AWS IAM permissions
                  restrict the Lambda
                  function to the
                  SentinelVision
                  resources it needs.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Serverless
                </strong>

                <p>
                  API Gateway and
                  Lambda execute on
                  demand without
                  requiring a
                  continuously running
                  application server.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Event ready
                </strong>

                <p>
                  S3 uploads can later
                  trigger OpenCV
                  processing and
                  metadata extraction
                  asynchronously.
                </p>
              </div>
            </div>
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* Platform architecture                                          */}
        {/* --------------------------------------------------------------- */}

        <section className="architecture-section">
          <div className="architecture-content">
            <span className="section-label">
              Platform architecture
            </span>

            <h2>
              Built as a serverless
              visual-data ingestion
              workflow
            </h2>

            <p>
              Files are uploaded
              directly to Amazon S3
              while AWS Lambda and API
              Gateway handle secure
              temporary upload
              authorization.
            </p>

            <div className="architecture-flow">
              <div>
                <strong>
                  React
                </strong>

                <span>
                  User interface
                </span>
              </div>

              <span className="flow-arrow">
                →
              </span>

              <div>
                <strong>
                  API Gateway
                </strong>

                <span>
                  HTTP API
                </span>
              </div>

              <span className="flow-arrow">
                →
              </span>

              <div>
                <strong>
                  AWS Lambda
                </strong>

                <span>
                  Presigned URL
                </span>
              </div>

              <span className="flow-arrow">
                →
              </span>

              <div>
                <strong>
                  Amazon S3
                </strong>

                <span>
                  Object storage
                </span>
              </div>
            </div>
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* System health                                                  */}
        {/* --------------------------------------------------------------- */}

        <section
          id="system"
          className="page-section"
        >
          <div className="system-card">
            <div>
              <span className="section-label">
                System health
              </span>

              <h2>
                SentinelVision
                services
              </h2>

              <p>
                The frontend
                communicates with the
                AWS API Gateway that
                powers secure
                serverless uploads.
              </p>
            </div>

            <div className="system-status-panel">
              <div className="system-service">
                <div>
                  <strong>
                    AWS Upload API
                  </strong>

                  <span>
                    API Gateway +
                    Lambda
                  </span>
                </div>

                <span
                  className={
                    apiStatus ===
                    "healthy"
                      ? "service-status online"
                      : "service-status offline"
                  }
                >
                  {
                    apiStatus
                  }
                </span>
              </div>

              <button
                type="button"
                className="refresh-button"
                onClick={
                  checkApiHealth
                }
              >
                Refresh status
              </button>

              {systemError && (
                <p className="inline-error">
                  {
                    systemError
                  }
                </p>
              )}
            </div>
          </div>
        </section>
      </main>


      {/* ----------------------------------------------------------------- */}
      {/* Footer                                                           */}
      {/* ----------------------------------------------------------------- */}

      <footer className="footer">
        <div className="footer-inner">
          <div>
            <strong>
              SentinelVision
            </strong>

            <p>
              Serverless visual-data
              ingestion and
              ML-readiness platform.
            </p>
          </div>

          <div className="footer-links">
            <a href="#home">
              Home
            </a>

            <a href="#analyse">
              Upload
            </a>

            <a href="#datasets">
              Datasets
            </a>

            <a href="#guide">
              Guide
            </a>
          </div>
        </div>
      </footer>
    </>
  );
}


export default App;
