import { useCallback, useEffect, useState } from "react";
import "./App.css";


// ===========================================================================
// API configuration
// ===========================================================================

// SentinelVision FastAPI backend.
//
// During local development:
// React / Vite -> http://localhost:5173
// FastAPI      -> http://127.0.0.1:8000
const API_BASE_URL = "http://127.0.0.1:8000";


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

  const units = ["Bytes", "KB", "MB", "GB"];
  const unitIndex = Math.floor(
    Math.log(bytes) / Math.log(1024)
  );

  const value = bytes / Math.pow(1024, unitIndex);

  return `${value.toFixed(2)} ${units[unitIndex]}`;
}


/**
 * Convert metadata field names into user-friendly labels.
 *
 * Example:
 * blur_score -> Blur Score
 *
 * @param {string} value Metadata property name.
 * @returns {string} Human-readable label.
 */
function formatLabel(value) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase()
    );
}


/**
 * Display metadata values cleanly.
 *
 * @param {*} value Metadata value.
 * @param {string} key Metadata key.
 * @returns {string} Formatted value.
 */
function formatMetadataValue(value, key) {
  if (value === null || value === undefined) {
    return "None";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (
    typeof value === "number" &&
    !Number.isInteger(value)
  ) {
    return value.toFixed(2);
  }

  if (key === "file_size_bytes") {
    return formatBytes(value);
  }

  return String(value);
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
            Analyse
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
 * Hero section explaining the product to first-time users.
 *
 * @param {string} apiStatus Current FastAPI health status.
 */
function Hero({ apiStatus }) {
  return (
    <section
      id="home"
      className="hero-section"
    >
      <div className="hero-content">
        <div className="eyebrow">
          ML-ready image & video quality analysis
        </div>

        <h1>
          Understand your visual data
          <span> before your model does.</span>
        </h1>

        <p className="hero-description">
          SentinelVision analyses images and videos for
          metadata, quality, integrity, dimensions and
          machine-learning readiness — automatically.
        </p>

        <div className="hero-actions">
          <a
            href="#analyse"
            className="primary-button"
          >
            Analyse your data
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
              apiStatus === "healthy"
                ? "status-dot status-dot-online"
                : "status-dot status-dot-offline"
            }
          />

          API status:

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
              <strong>Upload</strong>
              <small>
                Image or video
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              02
            </span>

            <div>
              <strong>Store</strong>
              <small>
                Secure Amazon S3 storage
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              03
            </span>

            <div>
              <strong>Analyse</strong>
              <small>
                OpenCV quality processing
              </small>
            </div>
          </div>

          <div className="pipeline-line" />

          <div className="pipeline-step">
            <span className="pipeline-number">
              04
            </span>

            <div>
              <strong>Inspect</strong>
              <small>
                ML-ready metadata
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
        <strong>Images</strong>
        <span>
          JPG · JPEG · PNG · AVIF
        </span>
      </div>

      <div className="stat">
        <strong>Videos</strong>
        <span>
          MP4 analysis
        </span>
      </div>

      <div className="stat">
        <strong>Integrity</strong>
        <span>
          SHA-256 fingerprints
        </span>
      </div>

      <div className="stat">
        <strong>Storage</strong>
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
  const inputId = `${mediaType}-file-input`;

  return (
    <div className="upload-card">
      <div className="upload-card-header">
        <div
          className={`media-icon ${mediaType}-icon`}
        >
          {mediaType === "image" ? "IMG" : "VID"}
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
              {formatBytes(file.size)}
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
        disabled={!file || uploading}
      >
        {uploading
          ? "Analysing..."
          : `Analyse ${mediaType}`
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
 * Quality overview for image metadata.
 */
function QualitySummary({ metadata }) {
  if (!metadata) {
    return null;
  }

  const brightnessNormal =
    metadata.brightness_warning === "Normal";

  const blurNormal =
    metadata.blur_warning === "Normal";

  const fileHealthy =
    metadata.is_corrupted === false;

  return (
    <div className="quality-grid">
      <div className="quality-card">
        <span>
          File integrity
        </span>

        <strong>
          {fileHealthy ? "Valid" : "Problem"}
        </strong>

        <span
          className={
            fileHealthy
              ? "quality-good"
              : "quality-warning"
          }
        >
          {fileHealthy ? "Passed" : "Check required"}
        </span>
      </div>

      {"brightness" in metadata && (
        <div className="quality-card">
          <span>
            Brightness
          </span>

          <strong>
            {Number(
              metadata.brightness
            ).toFixed(2)}
          </strong>

          <span
            className={
              brightnessNormal
                ? "quality-good"
                : "quality-warning"
            }
          >
            {metadata.brightness_warning}
          </span>
        </div>
      )}

      {"blur_score" in metadata && (
        <div className="quality-card">
          <span>
            Blur score
          </span>

          <strong>
            {Number(
              metadata.blur_score
            ).toFixed(2)}
          </strong>

          <span
            className={
              blurNormal
                ? "quality-good"
                : "quality-warning"
            }
          >
            {blurNormal
              ? "Sharp"
              : "Potential blur"
            }
          </span>
        </div>
      )}

      {"width" in metadata &&
        "height" in metadata && (
          <div className="quality-card">
            <span>
              Resolution
            </span>

            <strong>
              {metadata.width} × {metadata.height}
            </strong>

            <span className="quality-neutral">
              pixels
            </span>
          </div>
        )}
    </div>
  );
}


/**
 * Full analysis result returned from FastAPI.
 */
function AnalysisResult({ response }) {
  if (!response) {
    return null;
  }

  const metadata = response.result?.metadata;

  return (
    <section className="result-panel">
      <div className="section-heading">
        <div>
          <span className="section-label">
            Analysis complete
          </span>

          <h2>
            Your results
          </h2>
        </div>

        <span className="success-pill">
          Success
        </span>
      </div>

      <div className="result-message">
        <strong>
          {response.result?.original_filename}
        </strong>

        <span>
          {response.message}
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
              "[SentinelVision] Dataset ID copied to clipboard:",
              response.dataset_id
            );
          }}
        >
          Copy ID
        </button>
      </div>

      <h3 className="subsection-title">
        Quality overview
      </h3>

      <QualitySummary
        metadata={metadata}
      />

      <h3 className="subsection-title">
        Technical metadata
      </h3>

      <div className="metadata-table">
        {metadata &&
          Object.entries(metadata).map(
            ([key, value]) => (
              <div
                className="metadata-row"
                key={key}
              >
                <span>
                  {formatLabel(key)}
                </span>

                <strong>
                  {formatMetadataValue(
                    value,
                    key
                  )}
                </strong>
              </div>
            )
          )}
      </div>

      <div className="storage-information">
        <strong>
          Cloud storage
        </strong>

        <code>
          {response.result?.s3_key}
        </code>
      </div>
    </section>
  );
}


/**
 * Dataset information returned from /datasets/{dataset_id}.
 */
function DatasetDetails({ dataset }) {
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
            {dataset.images?.length ?? 0}
          </strong>

          <span>
            Images
          </span>
        </div>

        <div>
          <strong>
            {dataset.videos?.length ?? 0}
          </strong>

          <span>
            Videos
          </span>
        </div>
      </div>

      {dataset.images?.map(
        (image, index) => (
          <div
            className="dataset-media-item"
            key={`image-${index}`}
          >
            <div>
              <span className="dataset-type">
                IMAGE
              </span>

              <strong>
                {image.original_filename}
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
        (video, index) => (
          <div
            className="dataset-media-item"
            key={`video-${index}`}
          >
            <div>
              <span className="dataset-type">
                VIDEO
              </span>

              <strong>
                {video.original_filename}
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

  const [apiStatus, setApiStatus] =
    useState("Checking...");

  const [systemError, setSystemError] =
    useState("");


  // -------------------------------------------------------------------------
  // Upload state
  // -------------------------------------------------------------------------

  const [imageFile, setImageFile] =
    useState(null);

  const [videoFile, setVideoFile] =
    useState(null);

  const [uploadingType, setUploadingType] =
    useState("");

  const [uploadError, setUploadError] =
    useState("");

  const [analysisResult, setAnalysisResult] =
    useState(null);


  // -------------------------------------------------------------------------
  // Dataset state
  // -------------------------------------------------------------------------

  const [datasets, setDatasets] =
    useState([]);

  const [datasetQuery, setDatasetQuery] =
    useState("");

  const [datasetDetails, setDatasetDetails] =
    useState(null);

  const [datasetError, setDatasetError] =
    useState("");

  const [datasetLoading, setDatasetLoading] =
    useState(false);


  // -------------------------------------------------------------------------
  // API health check
  // -------------------------------------------------------------------------

  const checkApiHealth = useCallback(
    async () => {
      console.info(
        "[SentinelVision] Checking API health..."
      );

      try {
        const response = await fetch(
          `${API_BASE_URL}/health`
        );

        if (!response.ok) {
          throw new Error(
            `Health endpoint returned HTTP ${response.status}`
          );
        }

        const data = await response.json();

        console.info(
          "[SentinelVision] API health check successful:",
          data
        );

        setApiStatus(data.status);
        setSystemError("");
      } catch (error) {
        console.error(
          "[SentinelVision] API health check failed:",
          error
        );

        setApiStatus("Unavailable");

        setSystemError(
          "The SentinelVision API cannot currently be reached."
        );
      }
    },
    []
  );


  // -------------------------------------------------------------------------
  // Dataset list retrieval
  // -------------------------------------------------------------------------

  const loadDatasets = useCallback(
    async () => {
      console.info(
        "[SentinelVision] Loading dataset history..."
      );

      try {
        const response = await fetch(
          `${API_BASE_URL}/datasets`
        );

        if (!response.ok) {
          throw new Error(
            `Dataset endpoint returned HTTP ${response.status}`
          );
        }

        const data = await response.json();

        console.info(
          "[SentinelVision] Dataset history loaded:",
          data.dataset_count
        );

        setDatasets(data.datasets || []);
      } catch (error) {
        console.error(
          "[SentinelVision] Failed to load dataset history:",
          error
        );
      }
    },
    []
  );


  // -------------------------------------------------------------------------
  // Initial application loading
  // -------------------------------------------------------------------------

  useEffect(() => {
    console.info(
      "[SentinelVision] React application started."
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

  function handleImageSelection(event) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    console.info(
      "[SentinelVision] Image selected:",
      selectedFile.name,
      selectedFile.size,
      "bytes"
    );

    setImageFile(selectedFile);
    setUploadError("");
  }


  function handleVideoSelection(event) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    console.info(
      "[SentinelVision] Video selected:",
      selectedFile.name,
      selectedFile.size,
      "bytes"
    );

    setVideoFile(selectedFile);
    setUploadError("");
  }


  // -------------------------------------------------------------------------
  // Upload and analysis
  // -------------------------------------------------------------------------

  async function uploadMedia(
    mediaType,
    file
  ) {
    if (!file) {
      setUploadError(
        `Please choose a ${mediaType} first.`
      );

      console.warn(
        `[SentinelVision] ${mediaType} upload attempted without a file.`
      );

      return;
    }

    console.info(
      `[SentinelVision] Starting ${mediaType} upload:`,
      file.name
    );

    setUploadingType(mediaType);
    setUploadError("");
    setAnalysisResult(null);

    const formData = new FormData();

    formData.append(
      "file",
      file
    );

    try {
      const response = await fetch(
        `${API_BASE_URL}/upload/${mediaType}`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        const message =
          data.detail ||
          `Upload failed with HTTP ${response.status}`;

        throw new Error(message);
      }

      console.info(
        `[SentinelVision] ${mediaType} analysis completed successfully:`,
        data.dataset_id
      );

      setAnalysisResult(data);

      // Refresh the dataset history after successful processing.
      await loadDatasets();

      // Automatically bring the completed analysis into view.
      window.setTimeout(() => {
        document
          .getElementById("analysis-result")
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
      }, 100);
    } catch (error) {
      console.error(
        `[SentinelVision] ${mediaType} upload failed:`,
        error
      );

      setUploadError(
        error.message ||
        "The file could not be processed."
      );
    } finally {
      setUploadingType("");

      console.info(
        `[SentinelVision] ${mediaType} upload request finished.`
      );
    }
  }


  // -------------------------------------------------------------------------
  // Dataset lookup
  // -------------------------------------------------------------------------

  async function lookupDataset(event) {
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
      "[SentinelVision] Looking up dataset:",
      datasetId
    );

    setDatasetLoading(true);
    setDatasetError("");
    setDatasetDetails(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/datasets/${encodeURIComponent(
          datasetId
        )}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Dataset could not be found."
        );
      }

      console.info(
        "[SentinelVision] Dataset lookup successful:",
        datasetId
      );

      setDatasetDetails(data);
    } catch (error) {
      console.error(
        "[SentinelVision] Dataset lookup failed:",
        error
      );

      setDatasetError(
        error.message
      );
    } finally {
      setDatasetLoading(false);
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
          apiStatus={apiStatus}
        />

        <FeatureStats />


        {/* --------------------------------------------------------------- */}
        {/* Upload and analysis                                             */}
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
                Analyse visual data
              </h2>

              <p>
                Choose an image or video. SentinelVision
                will securely upload the file, extract
                technical metadata and run automated
                quality checks.
              </p>
            </div>
          </div>

          <div className="upload-grid">
            <UploadCard
              mediaType="image"
              title="Analyse an image"
              description={
                "Inspect brightness, blur, resolution, integrity and SHA-256 metadata."
              }
              accept=".jpg,.jpeg,.png,.avif"
              file={imageFile}
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
                uploadingType === "image"
              }
            />

            <UploadCard
              mediaType="video"
              title="Analyse a video"
              description={
                "Inspect resolution, frame rate, frame count, duration and integrity."
              }
              accept=".mp4"
              file={videoFile}
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
                uploadingType === "video"
              }
            />
          </div>

          {uploadError && (
            <div className="error-banner">
              <strong>
                Analysis failed
              </strong>

              <span>
                {uploadError}
              </span>
            </div>
          )}

          <div id="analysis-result">
            <AnalysisResult
              response={analysisResult}
            />
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* Dataset explorer                                                */}
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
                Find previous analyses
              </h2>

              <p>
                Every completed analysis receives a
                unique dataset ID. Use it to inspect
                results from the current API session.
              </p>
            </div>
          </div>

          <div className="dataset-layout">
            <div className="dataset-search-card">
              <h3>
                Search by dataset ID
              </h3>

              <p>
                Paste the ID returned after an upload.
              </p>

              <form
                onSubmit={lookupDataset}
                className="dataset-search-form"
              >
                <input
                  type="text"
                  value={datasetQuery}
                  onChange={(event) =>
                    setDatasetQuery(
                      event.target.value
                    )
                  }
                  placeholder="e.g. f1394d7e-066f-4cb8..."
                />

                <button
                  type="submit"
                  disabled={datasetLoading}
                >
                  {datasetLoading
                    ? "Searching..."
                    : "Find dataset"
                  }
                </button>
              </form>

              {datasetError && (
                <p className="inline-error">
                  {datasetError}
                </p>
              )}

              <DatasetDetails
                dataset={datasetDetails}
              />
            </div>

            <div className="recent-datasets-card">
              <div className="card-title-row">
                <div>
                  <h3>
                    Recent datasets
                  </h3>

                  <p>
                    Current API session
                  </p>
                </div>

                <span className="count-badge">
                  {datasets.length}
                </span>
              </div>

              {datasets.length === 0 ? (
                <div className="empty-state">
                  <strong>
                    No datasets yet
                  </strong>

                  <span>
                    Analyse an image or video to
                    create your first dataset.
                  </span>
                </div>
              ) : (
                <div className="recent-dataset-list">
                  {datasets.map(
                    (dataset) => (
                      <button
                        type="button"
                        className="recent-dataset"
                        key={
                          dataset.dataset_id
                        }
                        onClick={() => {
                          console.info(
                            "[SentinelVision] Dataset selected from history:",
                            dataset.dataset_id
                          );

                          setDatasetQuery(
                            dataset.dataset_id
                          );
                        }}
                      >
                        <code>
                          {dataset.dataset_id}
                        </code>

                        <span>
                          {dataset.image_count} image
                          {dataset.image_count !== 1
                            ? "s"
                            : ""}
                          {" · "}
                          {dataset.video_count} video
                          {dataset.video_count !== 1
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
        {/* User guidance                                                   */}
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
                You do not need to understand OpenCV,
                databases or cloud infrastructure to
                use the platform.
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
                Upload a supported image or MP4 video
                from your device.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                02
              </span>

              <h3>
                Secure processing
              </h3>

              <p>
                SentinelVision generates a unique
                dataset identifier and stores the raw
                file in a dataset-specific Amazon S3
                location.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                03
              </span>

              <h3>
                Automated analysis
              </h3>

              <p>
                OpenCV extracts dimensions, quality
                signals and technical metadata while
                SHA-256 creates a reproducible file
                fingerprint.
              </p>
            </article>

            <article className="guide-card">
              <span className="guide-number">
                04
              </span>

              <h3>
                Review results
              </h3>

              <p>
                Inspect quality warnings, metadata and
                your unique dataset ID directly in the
                browser.
              </p>
            </article>
          </div>


          <div className="metric-guide">
            <div className="metric-guide-heading">
              <span className="section-label">
                Understanding results
              </span>

              <h2>
                What do the metrics mean?
              </h2>
            </div>

            <div className="metric-list">
              <div className="metric-item">
                <strong>
                  Brightness
                </strong>

                <p>
                  Estimates the overall light intensity
                  of an image. SentinelVision flags
                  unusually dark or bright images using
                  its configured quality thresholds.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Blur score
                </strong>

                <p>
                  Estimates image sharpness. Lower
                  values may indicate an image that is
                  blurry or lacks sufficient visual
                  detail.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  SHA-256
                </strong>

                <p>
                  A deterministic fingerprint for a
                  file. SentinelVision uses hashes to
                  identify duplicate media reliably.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Resolution
                </strong>

                <p>
                  The width and height of visual media.
                  Resolution is important when checking
                  dataset consistency before machine
                  learning.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Frame rate
                </strong>

                <p>
                  For video files, FPS describes how
                  many frames occur each second and
                  helps identify inconsistent video
                  sources.
                </p>
              </div>

              <div className="metric-item">
                <strong>
                  Corruption check
                </strong>

                <p>
                  SentinelVision attempts to decode
                  uploaded media and identifies files
                  that cannot be processed correctly.
                </p>
              </div>
            </div>
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* Platform architecture                                           */}
        {/* --------------------------------------------------------------- */}

        <section className="architecture-section">
          <div className="architecture-content">
            <span className="section-label">
              Platform architecture
            </span>

            <h2>
              Built as a complete visual-data
              engineering workflow
            </h2>

            <p>
              The interface hides the infrastructure
              complexity while the backend handles
              analysis, storage and dataset
              organisation.
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
                  FastAPI
                </strong>

                <span>
                  REST API
                </span>
              </div>

              <span className="flow-arrow">
                →
              </span>

              <div>
                <strong>
                  OpenCV
                </strong>

                <span>
                  Visual analysis
                </span>
              </div>

              <span className="flow-arrow">
                →
              </span>

              <div>
                <strong>
                  AWS S3
                </strong>

                <span>
                  Object storage
                </span>
              </div>
            </div>
          </div>
        </section>


        {/* --------------------------------------------------------------- */}
        {/* System health                                                   */}
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
                SentinelVision services
              </h2>

              <p>
                The frontend continuously communicates
                with the FastAPI service that powers
                uploads and analysis.
              </p>
            </div>

            <div className="system-status-panel">
              <div className="system-service">
                <div>
                  <strong>
                    SentinelVision API
                  </strong>

                  <span>
                    FastAPI backend
                  </span>
                </div>

                <span
                  className={
                    apiStatus === "healthy"
                      ? "service-status online"
                      : "service-status offline"
                  }
                >
                  {apiStatus}
                </span>
              </div>

              <button
                type="button"
                className="refresh-button"
                onClick={checkApiHealth}
              >
                Refresh status
              </button>

              {systemError && (
                <p className="inline-error">
                  {systemError}
                </p>
              )}
            </div>
          </div>
        </section>
      </main>


      {/* ----------------------------------------------------------------- */}
      {/* Footer                                                            */}
      {/* ----------------------------------------------------------------- */}

      <footer className="footer">
        <div className="footer-inner">
          <div>
            <strong>
              SentinelVision
            </strong>

            <p>
              Visual data quality and
              ML-readiness platform.
            </p>
          </div>

          <div className="footer-links">
            <a href="#home">
              Home
            </a>

            <a href="#analyse">
              Analyse
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

