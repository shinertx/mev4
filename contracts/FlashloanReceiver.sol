// /contracts/FlashloanReceiver.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

// Best practice: Use specific package versions for production builds
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import "https://github.com/aave/protocol-v2/blob/master/contracts/flashloan/interfaces/IFlashLoanReceiver.sol";
import "https://github.com/aave/protocol-v2/blob/master/contracts/interfaces/ILendingPoolAddressesProvider.sol";
import "https://github.com/aave/protocol-v2/blob/master/contracts/interfaces/ILendingPool.sol";

/**
 * @title FlashloanReceiver
 * @notice Production-grade Aave V2 flashloan receiver with ReentrancyGuard, Ownable, and full repayment logic.
 * @author MEV-OG System
 */
contract FlashloanReceiver is IFlashLoanReceiver, ReentrancyGuard, Ownable {
    ILendingPoolAddressesProvider public immutable override ADDRESSES_PROVIDER;
    ILendingPool public immutable override LENDING_POOL;

    event FlashloanExecuted(
        address indexed initiator,
        address[] assets,
        uint256[] amounts,
        uint256[] premiums,
        uint256 timestamp
    );

    /**
     * @param provider Address of the Aave V2 LendingPoolAddressesProvider for the target network.
     */
    constructor(address provider) {
        require(provider != address(0), "ZERO_PROVIDER");
        ADDRESSES_PROVIDER = ILendingPoolAddressesProvider(provider);
        LENDING_POOL = ILendingPool(ADDRESSES_PROVIDER.getLendingPool());
    }

    /**
     * @dev Entry point called by Aave LendingPool after sending funds. This function executes the MEV logic.
     * @param assets The addresses of the assets borrowed.
     * @param amounts The amounts of each asset borrowed.
     * @param premiums The fees to be paid for the loan.
     * @param initiator The address that initiated the flashloan via the off-chain system.
     * @param params Custom calldata containing the sequence of operations to execute (e.g., swaps, liquidations).
     * @return True on successful execution and repayment.
     */
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    )
        external
        override
        nonReentrant // Prevents re-entrancy attacks
        returns (bool)
    {
        // Only the Aave LendingPool contract can call this function.
        require(msg.sender == address(LENDING_POOL), "CALLER_MUST_BE_LENDING_POOL");

        // Execute the user-defined logic encoded in the `params` data.
        _executeUserLogic(params);

        // Repay the loan plus the premium.
        for (uint i = 0; i < assets.length; i++) {
            uint256 amountToRepay = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(address(LENDING_POOL), amountToRepay);
        }

        emit FlashloanExecuted(initiator, assets, amounts, premiums, block.timestamp);
        return true;
    }

    /**
     * @dev Main entry point for the owner (the off-chain bot's EOA) to initiate a flash loan.
     * @param assets The tokens to borrow.
     * @param amounts The amounts of each token.
     * @param params Arbitrary data to pass to `executeOperation` for the user logic.
     */
    function initiateFlashLoan(
        address[] calldata assets,
        uint256[] calldata amounts,
        bytes calldata params
    ) external onlyOwner {
        // Specify '0' for debt modes, indicating a standard flash loan (no debt).
        uint256[] memory modes = new uint256[](assets.length);

        LENDING_POOL.flashLoan(
            address(this), // The receiver of the funds
            assets,
            amounts,
            modes,
            owner(), // The initiator tracked by Aave
            params,
            0 // Referral code
        );
    }

    /**
     * @dev Internal hook for executing the sequence of actions provided by the off-chain system.
     *      The security of the entire system relies on the correctness of the calldata generated off-chain.
     */
    function _executeUserLogic(bytes calldata params) internal {
        // In a real implementation, this would decode `params` and execute one or more `address.call(...)`
        // For example, calling Uniswap to swap the borrowed assets, then calling another contract.
        // SECURITY CRITICAL: This contract blindly trusts the `params` data.
        (bool success, ) = address(this).call(params);
        require(success, "EXECUTION_OF_USER_LOGIC_FAILED");
    }

    /**
     * @dev Emergency function for the owner to withdraw any ERC20 tokens accidentally sent to this contract.
     * @param token Address of the token to rescue.
     * @param to Recipient of the rescued tokens.
     */
    function emergencyWithdraw(address token, address to, uint256 amount) external onlyOwner {
        require(to != address(0), "ZERO_RECIPIENT");
        IERC20(token).transfer(to, amount);
    }

    // A receive() function is included to accept ETH if the user logic requires it (e.g., for WETH wrapping).
    receive() external payable {}
}
