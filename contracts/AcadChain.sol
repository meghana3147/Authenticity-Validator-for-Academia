// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title AcadChain Certificate Registry
 * @author AcadChain Team
 * @notice Stores and validates academic certificate hashes on Ethereum Sepolia Testnet
 *
 * SUPPLY CHAIN FLOW:
 *   University  →  issue()  →  Blockchain  →  verify()  →  Employer
 */
contract AcadChain {

    // ─── Data Structures ───────────────────────────────────────────────
    struct Certificate {
        bytes32  certHash;        // SHA-256 of certificate data
        address  issuer;          // University wallet that issued it
        string   certificateId;   // Human-readable ID  e.g. CERT-1234-ABCD
        string   studentName;
        string   degree;
        string   institution;
        uint256  issuedAt;        // Unix timestamp
        bool     isRevoked;
        bool     exists;
    }

    // ─── State ─────────────────────────────────────────────────────────
    address public owner;

    /// @dev certHash => Certificate struct
    mapping(bytes32 => Certificate) private certificates;

    /// @dev certificateId string => certHash  (for lookup by ID)
    mapping(string => bytes32) private idToHash;

    /// @dev approved university addresses
    mapping(address => bool) public approvedIssuers;

    // ─── Events ────────────────────────────────────────────────────────
    event CertificateIssued(
        bytes32 indexed certHash,
        address indexed issuer,
        string  certificateId,
        string  studentName,
        uint256 issuedAt
    );
    event CertificateRevoked(bytes32 indexed certHash, address indexed revokedBy);
    event IssuerApproved(address indexed issuer);
    event IssuerRevoked(address indexed issuer);

    // ─── Modifiers ─────────────────────────────────────────────────────
    modifier onlyOwner() {
        require(msg.sender == owner, "AcadChain: caller is not owner");
        _;
    }

    modifier onlyApprovedIssuer() {
        require(approvedIssuers[msg.sender], "AcadChain: not an approved issuer");
        _;
    }

    // ─── Constructor ───────────────────────────────────────────────────
    constructor() {
        owner = msg.sender;
        approvedIssuers[msg.sender] = true;  // owner is auto-approved
    }

    // ─── Admin Functions ───────────────────────────────────────────────

    /// @notice Approve a university wallet to issue certificates
    function approveIssuer(address _issuer) external onlyOwner {
        approvedIssuers[_issuer] = true;
        emit IssuerApproved(_issuer);
    }

    /// @notice Revoke a university's issuing rights
    function revokeIssuer(address _issuer) external onlyOwner {
        approvedIssuers[_issuer] = false;
        emit IssuerRevoked(_issuer);
    }

    // ─── Certificate Functions ─────────────────────────────────────────

    /**
     * @notice Issue a new certificate – stores its hash on-chain
     * @param _certHash      SHA-256 hash of the certificate data (bytes32)
     * @param _certificateId Human-readable certificate ID string
     * @param _studentName   Student full name
     * @param _degree        Degree title
     * @param _institution   Issuing institution name
     */
    function issueCertificate(
        bytes32 _certHash,
        string  calldata _certificateId,
        string  calldata _studentName,
        string  calldata _degree,
        string  calldata _institution
    ) external onlyApprovedIssuer {
        require(!certificates[_certHash].exists,    "AcadChain: certificate already exists");
        require(idToHash[_certificateId] == 0,      "AcadChain: certificateId already used");

        certificates[_certHash] = Certificate({
            certHash:      _certHash,
            issuer:        msg.sender,
            certificateId: _certificateId,
            studentName:   _studentName,
            degree:        _degree,
            institution:   _institution,
            issuedAt:      block.timestamp,
            isRevoked:     false,
            exists:        true
        });

        idToHash[_certificateId] = _certHash;

        emit CertificateIssued(_certHash, msg.sender, _certificateId, _studentName, block.timestamp);
    }

    /**
     * @notice Revoke a certificate (university or owner only)
     * @param _certHash SHA-256 hash of the certificate to revoke
     */
    function revokeCertificate(bytes32 _certHash) external {
        Certificate storage cert = certificates[_certHash];
        require(cert.exists, "AcadChain: certificate not found");
        require(
            cert.issuer == msg.sender || msg.sender == owner,
            "AcadChain: not authorised to revoke"
        );
        cert.isRevoked = true;
        emit CertificateRevoked(_certHash, msg.sender);
    }

    // ─── Verification Functions ────────────────────────────────────────

    /**
     * @notice Verify a certificate by its hash
     * @return exists    Whether it was ever issued
     * @return isRevoked Whether it has been revoked
     * @return issuer    University wallet address that issued it
     * @return issuedAt  Unix timestamp of issuance
     */
    function verifyCertificate(bytes32 _certHash)
        external view
        returns (
            bool    exists,
            bool    isRevoked,
            address issuer,
            uint256 issuedAt,
            string  memory studentName,
            string  memory degree,
            string  memory institution,
            string  memory certificateId
        )
    {
        Certificate storage cert = certificates[_certHash];
        return (
            cert.exists,
            cert.isRevoked,
            cert.issuer,
            cert.issuedAt,
            cert.studentName,
            cert.degree,
            cert.institution,
            cert.certificateId
        );
    }

    /**
     * @notice Look up a certificate by its human-readable ID
     */
    function getCertHashById(string calldata _certificateId)
        external view returns (bytes32)
    {
        return idToHash[_certificateId];
    }

    /**
     * @notice Quick boolean check – is this hash authentic and not revoked?
     */
    function isAuthentic(bytes32 _certHash) external view returns (bool) {
        Certificate storage cert = certificates[_certHash];
        return cert.exists && !cert.isRevoked;
    }
}
