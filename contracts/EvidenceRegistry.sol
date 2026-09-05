// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract EvidenceRegistry {
    struct Record {
        address submitter;
        uint256 timestamp;
    }

    mapping(bytes32 => Record) private records;

    event EvidenceRegistered(
        bytes32 indexed evidenceHash,
        address indexed submitter,
        uint256 timestamp
    );

    function register(bytes32 evidenceHash) external {
        require(
            records[evidenceHash].timestamp == 0,
            "Already registered"
        );

        records[evidenceHash] = Record(
            msg.sender,
            block.timestamp
        );

        emit EvidenceRegistered(
            evidenceHash,
            msg.sender,
            block.timestamp
        );
    }

    function isRegistered(bytes32 evidenceHash)
        external
        view
        returns (bool)
    {
        return records[evidenceHash].timestamp != 0;
    }

    function getRecord(bytes32 evidenceHash)
        external
        view
        returns (address submitter, uint256 timestamp)
    {
        Record memory rec = records[evidenceHash];
        require(rec.timestamp != 0, "Record not found");
        return (rec.submitter, rec.timestamp);
    }
}
