// /test/test_reentrancy_attack.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../contracts/FlashloanReceiver.sol";

contract MaliciousToken {
    FlashloanReceiver public victim;
    constructor(address _victim) {
        victim = FlashloanReceiver(_victim);
    }
    fallback() external {
        // attempt to re-enter
        try victim.executeFlashloan(address(this), 1, address(this)) {} catch {}
    }
}

contract ReentrancyTest is Test {
    FlashloanReceiver fl;
    MaliciousToken mt;

    function setUp() public {
        fl = new FlashloanReceiver();
        mt = new MaliciousToken(address(fl));
    }

    function testNoReentrancy() public {
        vm.expectRevert();
        fl.executeFlashloan(address(mt), 1, address(fl));
    }
}
