// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title Basic flashloan receiver example
/// @notice Minimal skeleton for integrating flashloan logic
/// @dev Assumes ERC3156-like callback interface
interface IFlashLoaner {
    function flashLoan(address receiver, address token, uint256 amount, bytes calldata data) external;
}

contract FlashloanReceiver {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Initiates a flashloan from a lender
    function start(address loaner, address token, uint256 amount, bytes calldata data) external onlyOwner {
        IFlashLoaner(loaner).flashLoan(address(this), token, amount, data);
    }

    /// @notice Called by the lender after transferring the loaned amount
    /// @dev Implement custom arbitrage or liquidation logic here
    function onFlashLoan(address token, uint256 amount, uint256 fee, bytes calldata data) external returns (bytes32) {
        // TODO: place your strategy here using `data` if needed

        // repay loan + fee
        IERC20(token).transfer(msg.sender, amount + fee);
        return keccak256("ERC3156FlashBorrower.onFlashLoan");
    }
}
